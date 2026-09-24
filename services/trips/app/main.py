#import httpx #used for communication between containers

#API communication between python moduls
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

DatabaseSession: TypeAlias = Annotated[Session, Depends(get_db)]


#Create a trip
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

    db.add(new_trip)
    db.commit()
    db.refresh(new_trip)

    return new_trip


#Fetch all trips
@app.get("/trips", response_model=list[TripResponse])
def get_trips(
    db: DatabaseSession,
):
    result = db.execute(select(Trip))

    return result.scalars().all()


#Get one trip
@app.get("/trips/{trip_id}", response_model=TripResponse)
def get_trip(
    trip_id: int,
    db: DatabaseSession,
):
    trip = db.get(Trip, trip_id)

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    return trip

#Update one trip
@app.put("/trips/{trip_id}", response_model=TripResponse)
def update_trip(
    trip_id: int,
    trip_data: TripCreate,
    db: DatabaseSession,
):
    trip = db.get(Trip, trip_id)

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    today = datetime.now(tz=ZoneInfo("Europe/Stockholm")).date()
    if trip_data.start_date > trip_data.end_date or trip_data.start_date < today:
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

#Delete an trip
@app.delete("/trips/{trip_id}")
def delete_trip(
    trip_id: int,
    db: DatabaseSession,
):
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
