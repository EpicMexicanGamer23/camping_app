import datetime
from typing import Literal

from pydantic import BaseModel

# Valid status values mirror the allowed column values in the ORM model
GearStatus = Literal["owned", "borrowed", "missing"]


class GearCreate(BaseModel):
    """Payload for creating or updating a gear item."""

    name: str
    description: str | None = None
    status: GearStatus
    return_date: datetime.date | None = None


class GearResponse(BaseModel):
    """Payload returned from all /gear endpoints."""

    id: int
    name: str
    description: str | None = None
    status: GearStatus
    return_date: datetime.date | None = None

    model_config = {"from_attributes": True}
