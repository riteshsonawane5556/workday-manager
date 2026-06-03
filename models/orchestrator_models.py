from dataclasses import dataclass, field
from pydantic import BaseModel

from models.email_models import ProcessingResult
from models.calendar_models import CalendarAnalysisResult


class PlannerDecision(BaseModel):
    intent: str
    needs_email: bool
    needs_calendar: bool
    needs_clarification: bool
    clarification_question: str | None = None


class OrchestratorRequest(BaseModel):
    message: str


class OrchestratorResult(BaseModel):
    summary: str
    email_result: ProcessingResult | None = None
    calendar_result: CalendarAnalysisResult | None = None
    clarification_question: str | None = None


@dataclass
class OrchestratorState:
    query: str
    decision: PlannerDecision | None = field(default=None)
    email_result: ProcessingResult | None = field(default=None)
    calendar_result: CalendarAnalysisResult | None = field(default=None)
