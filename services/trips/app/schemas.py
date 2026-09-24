from datetime import date, datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel


class TripCreate(BaseModel):
    location: str = "London"
    start_date: date = datetime.now(tz=ZoneInfo("Europe/Stockholm")).date()
    end_date: date = datetime.now(tz=ZoneInfo("Europe/Stockholm")).date()
    description: str | None = None

class TripResponse(BaseModel):
    id: int
    location: str
    start_date: date
    end_date: date
    description: str | None

    #here:
    model_config = {
        "from_attributes": True
    }