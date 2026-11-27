import os
from typing import Annotated, TypeAlias
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Gear, Gear_List
from .schema import (
    GearCreate,
    GearListEntryCreate,
    GearListEntryResponse,
    GearResponse,
)

#Used to fetch trip data from the trips service (relevant for trip_id validation)
TRIPS_SERVICE_URL = os.getenv("TRIPS_SERVICE_URL", "http://trips:8000")
_TIMEOUT = httpx.Timeout(5.0)


app = FastAPI(
    title="Gear Service",
    description="A microservice used for managing hiking gear items and trip gear lists.",
    version="1.0.0",
)

# Creates database tables on startup
Base.metadata.create_all(bind=engine)

#Establishes connection to database (SessionLocal) and yields it to the route handler. 
# Closes the session after the request is completed.
DatabaseSession: TypeAlias = Annotated[Session, Depends(get_db)]

"""Helper-function to fetch trip name."""
async def _fetch_trip_name(trip_id: int, client: httpx.AsyncClient) -> str:
    try:
        response = await client.get(f"{TRIPS_SERVICE_URL}/trips/{trip_id}")
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Trip {trip_id} not found",
            ) from e
        raise HTTPException(
            status_code=503,
            detail="Trips service unavailable: cannot verify trip ID",
        ) from e
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail="Trips service unavailable: cannot verify trip ID",
        ) from e

    try:
        trip_name = response.json().get("location")
    except (ValueError, AttributeError) as e:
        raise HTTPException(
            status_code=502,
            detail="Trips service returned invalid trip data",
        ) from e
    if not isinstance(trip_name, str):
        raise HTTPException(
            status_code=502,
            detail="Trips service returned invalid trip data",
        )
    return trip_name

"""Helper function which returns GearListEntryResponse."""
def _gear_list_entry_response(
    entry: Gear_List,
    trip_name: str,
) -> GearListEntryResponse:
    return GearListEntryResponse(
        trip_id=entry.trip_id,
        gear_id=entry.gear_id,
        trip_name=trip_name,
        gear_name=entry.gear.name,
    )



"""Add a new gear item. Status defaults to 'owned', return_date to null."""
@app.post("/gear", response_model=GearResponse)
def create_gear(gear: GearCreate, db: DatabaseSession):
    
    new_item = Gear(
        name=gear.name,
        description=gear.description,
        status=gear.status, #Status and return-date defaults are set in schema.py
        return_date=gear.return_date,
    )

    # Validation checks for gear item creation
    if new_item.name.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="Gear name cannot be empty.",
        )
    if new_item.status == "owned":
        new_item.return_date = None  # Ensure return_date is null for owned gear
    if new_item.status in ["borrowed", "missing"] and new_item.return_date is None:
        raise HTTPException(
            status_code=400,
            detail="Return date must be provided for gear with status 'borrowed' or 'missing'.",
        )
    if new_item.status in ["borrowed", "missing"] and new_item.return_date <= datetime.now(tz=ZoneInfo("Europe/Stockholm")).date():
        raise HTTPException(
            status_code=400,
            detail="Return date must be same date or after the current date for gear with status 'borrowed' or 'missing'.",
        )
    
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


"""Return all gear items."""
@app.get("/gear", response_model=list[GearResponse])
def get_all_gear(db: DatabaseSession):
    #Fetches all gear items from the database and returns them as a list of GearResponse objects.
    result = db.execute(select(Gear))

    #Validation for empty gear list
    if result is None:
        raise HTTPException(
            status_code=404, 
            detail="No gear items found"
        )
    return result.scalars().all()


"""Return a single gear item by ID."""
@app.get("/gear/{gear_id}", response_model=GearResponse)
def get_gear(gear_id: int, db: DatabaseSession):
    #Fetches a single gear item from the database by its ID and returns it as a GearResponse object.
    item = db.get(Gear, gear_id)

    #validation for gear item not found
    if item is None:
        raise HTTPException(
            status_code=404, 
            detail="Gear item not found"
        )
    return item


"""Update an existing gear item."""
@app.put("/gear/{gear_id}", response_model=GearResponse)
def update_gear(gear_id: int, gear_data: GearCreate, db: DatabaseSession):
    #Fetches a single gear item from the database by its ID and returns it as a GearResponse object.
    item = db.get(Gear, gear_id)

    #Validation checks for gear item update
    if item is None:
        raise HTTPException(
            status_code=404, 
            detail="Gear item not found"
        )
    if gear_data.name.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="Gear name cannot be empty.",
        )
    if gear_data.status == "owned" and gear_data.return_date is not None:
        raise HTTPException(
            status_code=400,
            detail="Return date must be null for gear with status 'owned'.",
        )
    if gear_data.status in ["borrowed", "missing"] and gear_data.return_date is None:
        raise HTTPException(
            status_code=400,
            detail="Return date must be provided for gear with status 'borrowed' or 'missing'.",
        )

    item.name = gear_data.name
    item.description = gear_data.description
    item.status = gear_data.status
    item.return_date = gear_data.return_date

    db.commit()
    db.refresh(item)
    return item


"""Delete a gear item by ID and remove all gear_list entries referencing this item."""
@app.delete("/gear/{gear_id}")
def delete_gear(gear_id: int, db: DatabaseSession):
    #Fetches a single gear item from the database by its ID and returns delete message.
    item = db.get(Gear, gear_id)
    if item is None:
        raise HTTPException(
            status_code=404, 
            detail="Gear item not found"
        )

    db.delete(item)
    db.commit()
    return {
        "message": "Gear deleted", 
        "id": gear_id}


#==============================================================================


"""Add a gear item to a trip's gear list."""
@app.post("/gear-list", response_model=GearListEntryResponse, status_code=201)
async def add_gear_to_list(entry: GearListEntryCreate, db: DatabaseSession):
    #Validates that gear item exists
    gear = db.get(Gear, entry.gear_id)
    if gear is None:
        raise HTTPException(
            status_code=404, 
            detail="Gear item not found"
        )
    #Makes a request to the trips service to validate that the trip exists. 
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        trip_name = await _fetch_trip_name(entry.trip_id, client)

    #Association table entry is created linking the gear item to the trip. 
    new_entry = Gear_List(
        trip_id=entry.trip_id,
        gear_id=entry.gear_id,
    )

    # The new entry is added to the database and returned in the response.
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return GearListEntryResponse(
        trip_id=new_entry.trip_id,
        gear_id=new_entry.gear_id,
        trip_name=trip_name,
        gear_name=gear.name,
    )


"""Return all gear list entries across all trips."""
@app.get("/gear-list", response_model=list[GearListEntryResponse])
async def get_full_gear_list(db: DatabaseSession):
    #Fetches all gear lists from the database and returns them as lists of GearListEntryResponse objects.
    result = db.execute(select(Gear_List))
    entries = result.scalars().all()
    trip_names: dict[int, str] = {}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for entry in entries:
            if entry.trip_id not in trip_names:
                trip_names[entry.trip_id] = await _fetch_trip_name(entry.trip_id, client)

    return [
        _gear_list_entry_response(entry, trip_names[entry.trip_id])
        for entry in entries
    ]


"""Returns the gear-list assigned to a specific trip."""
@app.get("/gear-list/trip/{trip_id}", response_model=list[GearListEntryResponse])
async def get_gear_list_for_trip(trip_id: int, db: DatabaseSession):
    #Fetches a specific gear-list from the database by searching for its trip-id and returns it as list of GearListEntryResponse.
    result = db.execute(select(Gear_List).where(Gear_List.trip_id == trip_id))
    entries = result.scalars().all()
    if not entries:
        return []

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        trip_name = await _fetch_trip_name(trip_id, client)
    return [_gear_list_entry_response(entry, trip_name) for entry in entries]


"""Remove a gear item from a trip's gear list by composite key (trip_id, gear_id)."""
@app.delete("/gear-list/{trip_id}/{gear_id}")
def remove_gear_from_list(trip_id: int, gear_id: int, db: DatabaseSession):
    #Fetches a specific gear-list based on trip_id and gear_id from the database and deletes it. Returns a message confirming deletion.
    entry = db.execute(
        select(Gear_List).
        where(Gear_List.trip_id == trip_id,Gear_List.gear_id == gear_id)
        ).scalar_one_or_none()
    #Validates if entry exists
    if entry is None:
        raise HTTPException(
            status_code=404, 
            detail="Gear list entry not found"
        )

    db.delete(entry)
    db.commit()
    return {
        "message": "Gear list entry removed", 
        "trip_id": trip_id,
        "gear_id": gear_id,
        }

