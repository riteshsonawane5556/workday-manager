from dataclasses import dataclass
from pydantic import BaseModel


class CalendarEvent(BaseModel):
    id: str
    title: str
    start_time: int
    end_time: int
    participants: list[str]


class ConflictPair(BaseModel):
    event_a: CalendarEvent
    event_b: CalendarEvent


@dataclass
class CalendarDeps:
    user_tz: str
    now_unix: int
    now_label: str
    changed_calendar: bool = False
    sink: object | None = None


class CalendarActionResult(BaseModel):
    description: str
    executed: bool
    awaiting_user: bool = False
