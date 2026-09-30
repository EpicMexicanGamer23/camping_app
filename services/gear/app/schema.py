import datetime
from typing import Literal

from pydantic import BaseModel

#Gear has three states: owned, borrowed, missing
GearStatus = Literal["owned", "borrowed", "missing"]

#-----------------Gear Items schema-------------------------:

#A payload for creating or updating a gear item.
class GearCreate(BaseModel):

    name: str
    description: str | None = None
    status: GearStatus = "owned"    #default set as 'owned' for status and None for return_date.
    return_date: datetime.date | None = None

#A payload returned from all /gear endpoints.
class GearResponse(BaseModel):

    id: int
    name: str
    description: str | None = None
    status: GearStatus
    return_date: datetime.date | None = None

    model_config = {"from_attributes": True}


#-------------------Gear List schema:-------------------------

#A payload for adding a gear item to a trip's gear list.
class GearListEntryCreate(BaseModel):

    trip_id: int
    gear_id: int


#A single row in the gear_list association table.
class GearListEntryResponse(BaseModel):

    trip_id: int
    gear_id: int

    model_config = {"from_attributes": True}
