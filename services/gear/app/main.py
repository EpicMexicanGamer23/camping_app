from typing import Annotated, TypeAlias

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Gear
from .schema import GearCreate, GearResponse

app = FastAPI(
    title="Gear-List Service",
    description="Microservice for managing hiking gear items",
    version="1.0.0",
)

# Create database tables on startup.
# here: For production use Alembic migrations instead.
Base.metadata.create_all(bind=engine)

DatabaseSession: TypeAlias = Annotated[Session, Depends(get_db)]



@app.post("/gear", response_model=GearResponse, status_code=201)
def create_gear(gear: GearCreate, db: DatabaseSession):
    """Add a new gear item."""
    new_item = Gear(
        name=gear.name,
        description=gear.description,
        status=gear.status,
        return_date=gear.return_date,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@app.get("/gear", response_model=list[GearResponse])
def get_all_gear(db: DatabaseSession):
    """Return all gear items."""
    result = db.execute(select(Gear))
    return result.scalars().all()


@app.get("/gear/{gear_id}", response_model=GearResponse)
def get_gear(gear_id: int, db: DatabaseSession):
    """Return a single gear item by ID."""
    item = db.get(Gear, gear_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Gear item not found")
    return item


@app.put("/gear/{gear_id}", response_model=GearResponse)
def update_gear(gear_id: int, gear_data: GearCreate, db: DatabaseSession):
    """Update an existing gear item."""
    item = db.get(Gear, gear_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Gear item not found")

    item.name = gear_data.name
    item.description = gear_data.description
    item.status = gear_data.status
    item.return_date = gear_data.return_date

    db.commit()
    db.refresh(item)
    return item


@app.delete("/gear/{gear_id}")
def delete_gear(gear_id: int, db: DatabaseSession):
    """Delete a gear item by ID."""
    item = db.get(Gear, gear_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Gear item not found")

    db.delete(item)
    db.commit()
    return {"message": "Gear deleted", "id": gear_id}

