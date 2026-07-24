import asyncio
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config.nylas_client import nylas, NYLAS_GRANT_ID
from models.calendar_models import CalendarEvent

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _user_tz() -> ZoneInfo:
    return ZoneInfo(os.environ.get("USER_TIMEZONE", "Asia/Kolkata"))


def clock_to_unix(day_offset: int, hour: int, minute: int) -> int:
    tz = _user_tz()
    now = datetime.now(tz)
    target_day = (now + timedelta(days=day_offset)).date()
    target = datetime(
        target_day.year, target_day.month, target_day.day, hour, minute, tzinfo=tz
    )
    return int(target.timestamp())


def _valid_emails(participants: list[str] | None) -> list[str]:
    if not participants:
        return []
    return [e.strip() for e in participants if e and _EMAIL_RE.match(e.strip())]


def _day_range_unix(start_offset: int, num_days: int) -> tuple[int, int]:
    tz = _user_tz()
    now = datetime.now(tz)
    start_day = (now + timedelta(days=start_offset)).date()
    start = int(
        datetime(start_day.year, start_day.month, start_day.day, tzinfo=tz).timestamp()
    )
    end = start + num_days * 86400
    return start, end


def _fetch_events_range(start_offset: int, num_days: int) -> list[CalendarEvent]:
    calendars = nylas.calendars.list(NYLAS_GRANT_ID)
    if not calendars.data:
        return []
    calendar_id = calendars.data[0].id

    start, end = _day_range_unix(start_offset, num_days)

    response = nylas.events.list(
        NYLAS_GRANT_ID,
        query_params={"calendar_id": calendar_id, "start": start, "end": end},
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


async def fetch_events_range(start_offset: int = 0, num_days: int = 1) -> list[CalendarEvent]:
    if num_days <= 0:
        num_days = 1
    return await asyncio.to_thread(_fetch_events_range, start_offset, num_days)


async def fetch_today_events() -> list[CalendarEvent]:
    return await fetch_events_range(0, 1)


def _get_primary_calendar_id() -> str:
    calendars = nylas.calendars.list(NYLAS_GRANT_ID)
    if not calendars.data:
        raise ValueError("No calendars found on this account")
    return calendars.data[0].id


def _create_event(title: str, start_time: int, end_time: int, participants: list[str]) -> str:
    calendar_id = _get_primary_calendar_id()
    valid_participants = [{"email": e} for e in _valid_emails(participants)]
    body: dict = {
        "title": title,
        "when": {"start_time": start_time, "end_time": end_time},
        "calendar_id": calendar_id,
    }
    if valid_participants:
        body["participants"] = valid_participants
    result = nylas.events.create(
        NYLAS_GRANT_ID,
        request_body=body,
        query_params={"calendar_id": calendar_id, "notify_participants": True},
    )
    return result.data.id


def _update_event(
    event_id: str,
    title: str | None,
    start_time: int | None,
    end_time: int | None,
    participants: list[str] | None,
) -> None:
    calendar_id = _get_primary_calendar_id()
    body: dict = {}
    if title is not None:
        body["title"] = title
    if start_time is not None and end_time is not None:
        body["when"] = {"start_time": start_time, "end_time": end_time}
    valid_participants = _valid_emails(participants)
    if valid_participants:
        body["participants"] = [{"email": e} for e in valid_participants]
    nylas.events.update(
        NYLAS_GRANT_ID,
        event_id,
        request_body=body,
        query_params={"calendar_id": calendar_id, "notify_participants": True},
    )


def _delete_event(event_id: str) -> None:
    calendar_id = _get_primary_calendar_id()
    nylas.events.destroy(
        NYLAS_GRANT_ID,
        event_id,
        query_params={"calendar_id": calendar_id},
    )


async def create_event(title: str, start_time: int, end_time: int, participants: list[str]) -> str:
    return await asyncio.to_thread(_create_event, title, start_time, end_time, participants)


async def update_event(
    event_id: str,
    title: str | None,
    start_time: int | None,
    end_time: int | None,
    participants: list[str] | None = None,
) -> None:
    await asyncio.to_thread(_update_event, event_id, title, start_time, end_time, participants)


async def delete_event(event_id: str) -> None:
    await asyncio.to_thread(_delete_event, event_id)


def _add_participant(event_id: str, email: str) -> bool:
    if not _EMAIL_RE.match(email.strip()):
        return False
    calendar_id = _get_primary_calendar_id()
    event = nylas.events.find(NYLAS_GRANT_ID, event_id, query_params={"calendar_id": calendar_id})
    existing = {p.email for p in (event.data.participants or []) if getattr(p, "email", None)}
    if email.strip() in existing:
        return False
    participants = list(existing) + [email.strip()]
    nylas.events.update(
        NYLAS_GRANT_ID,
        event_id,
        request_body={"participants": [{"email": e} for e in participants]},
        query_params={"calendar_id": calendar_id, "notify_participants": True},
    )
    return True


async def add_participant(event_id: str, email: str) -> bool:
    return await asyncio.to_thread(_add_participant, event_id, email)
