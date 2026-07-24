from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from dataclasses import dataclass


class AgentDecision(BaseModel):
    intent: str
    next_node: str
    needs_email: bool
    needs_calendar: bool
    needs_clarification: bool
    clarification_question: str | None = None


@dataclass
class PlannerDeps:
    calendar_action_open: bool


planner_agent = Agent(
    "groq:llama-3.3-70b-versatile",
    deps_type=PlannerDeps,
    output_type=AgentDecision,
    retries=3,
    instructions="Retired — replaced by manager_agent.",
)


@planner_agent.instructions
def _calendar_action_hint(ctx: RunContext[PlannerDeps]) -> str | None:
    return None
