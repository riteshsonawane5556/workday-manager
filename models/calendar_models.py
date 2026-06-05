from dataclasses import dataclass
from typing import Literal, Optional
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


class RescheduleSuggestion(BaseModel):
    event_id: str
    title: str
    suggested_start: str
    reasoning: str


class CalendarAnalysisResult(BaseModel):
    date: str
    total_events: int
    conflicts: list[ConflictPair]
    suggestions: list[RescheduleSuggestion]
    summary: str


@dataclass
class CalendarDeps:
    user_tz: str
    now_unix: int
    now_label: str
    changed_calendar: bool = False


class CalendarActionResult(BaseModel):
    description: str
    executed: bool
    awaiting_user: bool = False
