import warnings
from dataclasses import dataclass, field

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from pydantic_graph import BaseNode, End, Graph, GraphRunContext

from agents.calendar_agent import calendar_agent
from models.calendar_models import CalendarAnalysisResult, CalendarEvent, ConflictPair
from services.calendar_service import fetch_calendar_data
from utils.calendar_utils import build_calendar_prompt
from config.logger import get_logger

log = get_logger("calendar_graph")


@dataclass
class CalendarPipelineState:
    events: list[CalendarEvent] = field(default_factory=list)
    conflicts: list[ConflictPair] = field(default_factory=list)
    date_str: str = ""


@dataclass
class FetchCalendarNode(BaseNode[CalendarPipelineState]):
    async def run(self, ctx: GraphRunContext[CalendarPipelineState]) -> "CalendarNode":
        log.info("FetchCalendarNode  →  fetching calendar data")
        ctx.state.events, ctx.state.conflicts, ctx.state.date_str = await fetch_calendar_data()
        log.info(
            "FetchCalendarNode  →  fetched %d events, %d conflicts for %s",
            len(ctx.state.events), len(ctx.state.conflicts), ctx.state.date_str,
        )
        return CalendarNode()


@dataclass
class CalendarNode(BaseNode[CalendarPipelineState]):
    async def run(self, ctx: GraphRunContext[CalendarPipelineState]) -> End[CalendarAnalysisResult]:
        log.info("CalendarNode  →  running calendar_agent on %d events", len(ctx.state.events))
        prompt = build_calendar_prompt(ctx.state.events, ctx.state.conflicts, ctx.state.date_str)
        result = await calendar_agent.run(prompt)
        output = result.output
        output.date = ctx.state.date_str
        output.total_events = len(ctx.state.events)
        output.conflicts = ctx.state.conflicts
        log.info("CalendarNode  →  analysis done: %d suggestions", len(output.suggestions))
        return End(output)


with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    calendar_graph = Graph(
        nodes=(FetchCalendarNode, CalendarNode),
        state_type=CalendarPipelineState,
    )


async def run_calendar_pipeline() -> CalendarAnalysisResult:
    log.info("=== Calendar pipeline START ===")
    state = CalendarPipelineState()
    result = await calendar_graph.run(FetchCalendarNode(), state=state)
    log.info("=== Calendar pipeline END ===")
    return result.output
