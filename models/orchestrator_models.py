from dataclasses import dataclass, field
from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage

from models.email_models import ProcessingResult
from models.calendar_models import CalendarActionResult


@dataclass
class RecentEvent:
    id: str
    title: str
    start_unix: int
    end_unix: int
    attendees: list[str] = field(default_factory=list)


@dataclass
class WorkdayMemory:
    recent_events: list[RecentEvent] = field(default_factory=list)
    email_pending_ids: list[str] = field(default_factory=list)
    calendar_changed: bool = False

    def record_event(self, e: RecentEvent) -> None:
        self.recent_events.append(e)


@dataclass
class WorkdayDeps:
    user_tz: str
    now_unix: int
    now_label: str
    working_memory: WorkdayMemory
    calendar_history: list[ModelMessage] = field(default_factory=list)


class ManagerOutput(BaseModel):
    summary: str
    clarification_question: str | None = None


class OrchestratorRequest(BaseModel):
    message: str
    session_id: str | None = None


class OrchestratorResult(BaseModel):
    summary: str
    session_id: str = ""
    email_result: ProcessingResult | None = None
    calendar_action_result: CalendarActionResult | None = None
    clarification_question: str | None = None
