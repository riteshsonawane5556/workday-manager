from dataclasses import dataclass, field
from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage

from models.email_models import EmailMeta, EmailNodeOutput, ProcessingResult
from models.calendar_models import CalendarAnalysisResult, CalendarActionResult, CalendarEvent, ConflictPair


class AgentDecision(BaseModel):
    intent: str
    next_node: str
    needs_email: bool
    needs_calendar: bool
    needs_clarification: bool
    clarification_question: str | None = None


class OrchestratorRequest(BaseModel):
    message: str
    session_id: str = "default"


class OrchestratorResult(BaseModel):
    summary: str
    email_result: ProcessingResult | None = None
    calendar_result: CalendarAnalysisResult | None = None
    calendar_action_result: CalendarActionResult | None = None
    clarification_question: str | None = None


@dataclass
class OrchestratorState:
    query: str
    planner_history: list[ModelMessage] = field(default_factory=list)
    calendar_action_history: list[ModelMessage] = field(default_factory=list)
    synthesize_history: list[ModelMessage] = field(default_factory=list)
    decision: AgentDecision | None = field(default=None)
    calendar_action_open: bool = False

    emails: list[EmailMeta] = field(default_factory=list)
    current_index: int = 0
    email_outputs: list[EmailNodeOutput] = field(default_factory=list)
    pending_ids: list[str] = field(default_factory=list)

    events: list[CalendarEvent] = field(default_factory=list)
    conflicts: list[ConflictPair] = field(default_factory=list)
    date_str: str = ""

    email_result: ProcessingResult | None = field(default=None)
    calendar_result: CalendarAnalysisResult | None = field(default=None)
    calendar_action_result: CalendarActionResult | None = field(default=None)
