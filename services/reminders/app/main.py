import logging
import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI

app = FastAPI(
    title="Reminders Service",
    description="Aggregates trip and gear data to surface upcoming reminders",
    version="1.0.0",
)

logger = logging.getLogger(__name__)

# Injected via storage.env — values match docker-compose service names so
# Docker's internal DNS resolves them correctly.
TRIPS_SERVICE_URL = os.getenv("TRIPS_SERVICE_URL", "http://trips:8000")
GEAR_SERVICE_URL = os.getenv("GEAR_SERVICE_URL", "http://gear:8000")

# Short timeout so one dead backend doesn't stall the whole response
_TIMEOUT = httpx.Timeout(5.0)


def _parse_date(value: str | None) -> date | None:
    """Parse an ISO date string (YYYY-MM-DD) into a date object, or return None."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


@app.get("/reminders")
async def get_reminders():
    """
    Calls the trips and gear services internally and returns:
    - next_trip_days:  days until the nearest upcoming trip (None if no trips)
    - next_trip_name:  location of that trip (None if no trips)
    - gear_reminders:  list of borrowed gear items with a return_date, sorted ascending
    """
    today = datetime.now(ZoneInfo("Europe/Stockholm")).date()

    # ------------------------------------------------------------------ trips
    next_trip_days: int | None = None
    next_trip_name: str | None = None

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(f"{TRIPS_SERVICE_URL}/trips")
            response.raise_for_status()
            trips = response.json()

        future_trips = []
        for trip in trips:
            start = _parse_date(trip.get("start_date"))
            if start and start >= today:
                future_trips.append((start, trip))

        if future_trips:
            future_trips.sort(key=lambda t: t[0])
            nearest_date, nearest_trip = future_trips[0]
            next_trip_days = (nearest_date - today).days
            next_trip_name = nearest_trip.get("location")

    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        # Trips service unreachable or returned bad data — return partial response
        logger.exception("Unable to retrieve or process trips")

    # ------------------------------------------------------------------- gear
    gear_reminders: list[dict] = []

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(f"{GEAR_SERVICE_URL}/gear")
            response.raise_for_status()
            gear_items = response.json()

        for item in gear_items:
            if item.get("status") == "borrowed" and item.get("return_date"):
                gear_reminders.append(
                    {
                        "gear_name": item.get("name"),
                        "type": "return",
                        "date": item.get("return_date"),
                    }
                )

        gear_reminders.sort(key=lambda r: r["date"])

    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        # Gear service unreachable or returned bad data — return partial response
        logger.exception("Unable to retrieve or process gear")

    return {
        "next_trip_days": next_trip_days,
        "next_trip_name": next_trip_name,
        "gear_reminders": gear_reminders,
    }
