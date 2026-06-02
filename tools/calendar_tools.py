import asyncio
from datetime import datetime, timezone

from config.nylas_client import nylas, NYLAS_GRANT_ID
from models.calendar_models import CalendarEvent


def _fetch_today_events() -> list[CalendarEvent]:
    calendars = nylas.calendars.list(NYLAS_GRANT_ID)
    if not calendars.data:
        return []
    calendar_id = calendars.data[0].id

    now = datetime.now(timezone.utc)
    start_of_day = int(datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp())
    end_of_day = start_of_day + 86400

    response = nylas.events.list(
        NYLAS_GRANT_ID,
        query_params={"calendar_id": calendar_id, "start": start_of_day, "end": end_of_day},
    )

    events: list[CalendarEvent] = []
    for event in response.data:
        when = event.when
        if not hasattr(when, "start_time") or not hasattr(when, "end_time"):
            continue
        participants = [
            p.email for p in (event.participants or []) if getattr(p, "email", None)
        ]
        events.append(
            CalendarEvent(
                id=event.id,
                title=event.title or "(no title)",
                start_time=when.start_time,
                end_time=when.end_time,
                participants=participants,
            )
        )
    return events


async def fetch_today_events() -> list[CalendarEvent]:
    return await asyncio.to_thread(_fetch_today_events)
