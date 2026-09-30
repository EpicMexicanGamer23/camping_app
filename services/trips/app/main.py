from datetime import datetime
from typing import Annotated, TypeAlias
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Trip
from .schemas import TripCreate, TripResponse

app = FastAPI(
    title="Trip Planner Service",
    description="A microservice for adding, updating or removing planned trips",
    version="1.0.0",
)

# Create database tables when the application starts.
Base.metadata.create_all(bind=engine)
#Change this later for database migrations (e.g. Alembic) after initial architecture is set

#Establishes connection to database (SessionLocal) and yields it to the route handler. 
# Closes the session after the request is completed.
DatabaseSession: TypeAlias = Annotated[Session, Depends(get_db)]


"""Add a new trip"""
@app.post("/trips", response_model=TripResponse)
def create_trip(
    trip: TripCreate,
    db: DatabaseSession,
):
    new_trip = Trip(
        location=trip.location,
        start_date=trip.start_date,
        end_date=trip.end_date,
        description=trip.description,
    )
    #Validation for location and trip dates
    if trip.location == "":
        raise HTTPException(
            status_code=400,
            detail="Location cannot be empty",
        )

    if (trip.start_date > trip.end_date) or (trip.start_date < datetime.now(tz=ZoneInfo("Europe/Stockholm")).date()):
        raise HTTPException(
            status_code=400,
            detail="Incorrect date input: less or greater issue",
        )
    

    db.add(new_trip)
    db.commit()
    db.refresh(new_trip)

    return new_trip


"""Return all trips."""
@app.get("/trips", response_model=list[TripResponse])
def get_trips(
    db: DatabaseSession,
):
    #Fetches all trips from the database and returns them as a list of TripResponse objects.
    result = db.execute(select(Trip))
    return result.scalars().all()


"""Return a single trip by ID."""
@app.get("/trips/{trip_id}", response_model=TripResponse)
def get_trip(
    trip_id: int,
    db: DatabaseSession,
):
    #Fetches a specific trip from the database by its ID and return it as a TripResponse object.
    trip = db.get(Trip, trip_id)

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    return trip

"""Update an existing trip."""
@app.put("/trips/{trip_id}", response_model=TripResponse)
def update_trip(
    trip_id: int,
    trip_data: TripCreate,
    db: DatabaseSession,
):
    #Fetches a specific trip from the database by its ID and return it as a TripResponse object.
    trip = db.get(Trip, trip_id)

    #Validation for trip id, location and trip dates
    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )
    if trip_data.location == "":
        raise HTTPException(
            status_code=400,
            detail="Location cannot be empty",
        )
    if (trip_data.start_date > trip.end_date) or (trip_data.start_date < datetime.now(tz=ZoneInfo("Europe/Stockholm")).date()):
        raise HTTPException(
            status_code=400,
            detail="Incorrect date input",
        )
    
    trip.location = trip_data.location
    trip.start_date = trip_data.start_date
    trip.end_date = trip_data.end_date
    trip.description = trip_data.description

    db.commit()
    db.refresh(trip)

    return trip

"""Delete a trip by ID"""
@app.delete("/trips/{trip_id}")
def delete_trip(
    trip_id: int,
    db: DatabaseSession,
):
    #Fetches a specific trip from the database by its ID and return a delete message.
    trip = db.get(Trip, trip_id)

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    db.delete(trip)
    db.commit()

    return {
        "message": "Trip deleted",
        "id": trip_id,
    }
