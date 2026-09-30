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

#Injected via storage.env matching kubernetes image. 
TRIPS_SERVICE_URL = os.getenv("TRIPS_SERVICE_URL", "http://trips:8000")
GEAR_SERVICE_URL = os.getenv("GEAR_SERVICE_URL", "http://gear:8000")

# Short timeout so one dead backend doesn't stall the whole response
_TIMEOUT = httpx.Timeout(5.0)


"""Parse an ISO date string (YYYY-MM-DD) into a date object, or return None."""
def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


@app.get("/reminders")
async def get_reminders():
    """
    Returns a reminder payload consisting of:

    - next_trip_days:  days until the nearest upcoming trip (null if none)
    - next_trip_name:  location of that trip (null if none)
    - trips:           all upcoming trips, each with their assigned packing list
    - gear_reminders:  gear items that need attention —
                        "missing" items (need to be sourced before the trip)
                        borrowed" items that have a return_date (need to be returned)
    """
    today = datetime.now(ZoneInfo("Europe/Stockholm")).date()

    # ------------------------------------------------------------------ trips
    next_trip_days: int | None = None
    next_trip_name: str | None = None
    trips_with_gear: list[dict] = []

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(f"{TRIPS_SERVICE_URL}/trips")
            response.raise_for_status()
            all_trips = response.json()

        # Keeps only future trips
        future_trips = []
        for trip in all_trips:
            start = _parse_date(trip.get("start_date"))
            if start and start >= today:
                future_trips.append((start, trip))

        #sorts future trips by first element: the trips start-date (resulting in next upcoming trip first)
        future_trips.sort(key=lambda t: t[0])

        if future_trips:
            nearest_date, nearest_trip = future_trips[0]
            next_trip_days = (nearest_date - today).days
            next_trip_name = nearest_trip.get("location")

        # For each future trip fetch its packing list from the gear service
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            for start_date, trip in future_trips:
                trip_id = trip.get("id")
                packing_list: list[dict] = []

                try:
                    gear_resp = await client.get(
                        f"{GEAR_SERVICE_URL}/gear-list/trip/{trip_id}"
                    )
                    gear_resp.raise_for_status()
                    entries = gear_resp.json()

                    for entry in entries:
                        gear = entry.get("gear", {})
                        packing_list.append(
                            {
                                "gear_id": gear.get("id"),
                                "name": gear.get("name"),
                                "status": gear.get("status"),
                            }
                        )
                except (httpx.HTTPError, ValueError, TypeError, KeyError):
                    # Gear list unavailable for this trip — include trip with empty list
                    logger.warning(
                        "Could not fetch gear list for trip %s", trip_id
                    )

                trips_with_gear.append(
                    {
                        "trip_id": trip_id,
                        "location": trip.get("location"),
                        "start_date": trip.get("start_date"),
                        "end_date": trip.get("end_date"),
                        "days_away": (start_date - today).days,
                        "packing_list": packing_list,
                    }
                )

    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        logger.exception("Unable to retrieve or process trips")



    # Map gear_id → earliest future trip start_date it is packed for.
    # trips_with_gear is already sorted ascending, so the first write per gear_id wins.
    # "missing" gear uses this as its urgency deadline instead of null.
    gear_id_to_trip_date: dict[int, str] = {}
    for trip_entry in trips_with_gear:
        trip_start = trip_entry.get("start_date")
        for packed in trip_entry.get("packing_list", []):
            gid = packed.get("gear_id")
            if gid not in gear_id_to_trip_date:
                gear_id_to_trip_date[gid] = trip_start

    # ------------------------------------------------------------------- gear
    # Remind about:
    #   - any item with status "missing" (needs to be sourced before its trip)
    #   - any item with status "borrowed" that has a return_date (needs returning)
    gear_reminders: list[dict] = []

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(f"{GEAR_SERVICE_URL}/gear")
            response.raise_for_status()
            gear_items = response.json()

        for item in gear_items:
            status = item.get("status")
            return_date = item.get("return_date")
            gear_id = item.get("id")

            if status == "missing":
                # Use the earliest trip start_date this gear is packed for,
                # or null if it isn't on any trip's packing list.
                trip_date = gear_id_to_trip_date.get(gear_id)
                gear_reminders.append(
                    {
                        "gear_name": item.get("name"),
                        "type": "missing",
                        "date": trip_date,
                    }
                )
            elif status == "borrowed" and return_date:
                gear_reminders.append(
                    {
                        "gear_name": item.get("name"),
                        "type": "return",
                        "date": return_date,
                    }
                )

        # Sort: dated items ascending, then undated (missing with no trip) last
        gear_reminders.sort(key=lambda r: (r["date"] is None, r["date"] or ""))

    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        logger.exception("Unable to retrieve or process gear")

    return {
        "next_trip_days": next_trip_days,
        "next_trip_name": next_trip_name,
        "trips": trips_with_gear,
        "gear_reminders": gear_reminders,
    }
