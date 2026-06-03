import warnings
from dataclasses import dataclass

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from pydantic_graph import BaseNode, End, Graph, GraphRunContext

from agents.planner_agent import planner_agent
from agents.synthesize_agent import synthesize_agent
from graph.email_graph import run_email_pipeline
from graph.calendar_graph import run_calendar_pipeline
from models.orchestrator_models import OrchestratorResult, OrchestratorState, PlannerDecision
from config.logger import get_logger

log = get_logger("orchestrator")


@dataclass
class PlannerNode(BaseNode[OrchestratorState]):
    async def run(
        self, ctx: GraphRunContext[OrchestratorState]
    ) -> "ClarifyNode | EmailPipelineNode | CalendarPipelineNode | SynthesizeNode":
        log.info("PlannerNode  →  running planner_agent on query: %r", ctx.state.query)
        result = await planner_agent.run(ctx.state.query)
        ctx.state.decision = result.output
        decision = ctx.state.decision
        log.info(
            "PlannerNode  →  decision: intent=%r  needs_email=%s  needs_calendar=%s  needs_clarification=%s",
            decision.intent, decision.needs_email, decision.needs_calendar, decision.needs_clarification,
        )

        if decision.needs_clarification:
            log.info("PlannerNode  →  routing to ClarifyNode")
            return ClarifyNode()
        if decision.needs_email:
            log.info("PlannerNode  →  routing to EmailPipelineNode")
            return EmailPipelineNode()
        if decision.needs_calendar:
            log.info("PlannerNode  →  routing to CalendarPipelineNode")
            return CalendarPipelineNode()
        log.info("PlannerNode  →  routing directly to SynthesizeNode (no pipeline needed)")
        return SynthesizeNode()


@dataclass
class ClarifyNode(BaseNode[OrchestratorState]):
    async def run(self, ctx: GraphRunContext[OrchestratorState]) -> End[OrchestratorResult]:
        log.info("ClarifyNode  →  query is ambiguous, returning clarification question")
        question = ctx.state.decision.clarification_question or "Could you clarify what you need help with?"
        return End(OrchestratorResult(
            summary=question,
            clarification_question=question,
        ))


@dataclass
class EmailPipelineNode(BaseNode[OrchestratorState]):
    async def run(
        self, ctx: GraphRunContext[OrchestratorState]
    ) -> "CalendarPipelineNode | SynthesizeNode":
        log.info("EmailPipelineNode  →  starting email pipeline")
        try:
            ctx.state.email_result = await run_email_pipeline()
            er = ctx.state.email_result
            log.info(
                "EmailPipelineNode  →  done: processed=%d  actionable=%d  pending_drafts=%d",
                er.processed, er.actionable, len(er.pending_ids),
            )
        except Exception as exc:
            log.error("EmailPipelineNode  →  pipeline failed: %s", exc, exc_info=True)
            ctx.state.email_result = None

        if ctx.state.decision.needs_calendar:
            log.info("EmailPipelineNode  →  calendar also needed, routing to CalendarPipelineNode")
            return CalendarPipelineNode()
        log.info("EmailPipelineNode  →  routing to SynthesizeNode")
        return SynthesizeNode()


@dataclass
class CalendarPipelineNode(BaseNode[OrchestratorState]):
    async def run(self, ctx: GraphRunContext[OrchestratorState]) -> "SynthesizeNode":
        log.info("CalendarPipelineNode  →  starting calendar pipeline")
        try:
            ctx.state.calendar_result = await run_calendar_pipeline()
            cr = ctx.state.calendar_result
            log.info(
                "CalendarPipelineNode  →  done: date=%s  total_events=%d  conflicts=%d",
                cr.date, cr.total_events, len(cr.conflicts),
            )
        except Exception as exc:
            log.error("CalendarPipelineNode  →  pipeline failed: %s", exc, exc_info=True)
            ctx.state.calendar_result = None
        log.info("CalendarPipelineNode  →  routing to SynthesizeNode")
        return SynthesizeNode()


@dataclass
class SynthesizeNode(BaseNode[OrchestratorState]):
    async def run(self, ctx: GraphRunContext[OrchestratorState]) -> End[OrchestratorResult]:
        log.info("SynthesizeNode  →  running synthesize_agent")
        lines = [
            f'User query: "{ctx.state.query}"',
            f'Intent: "{ctx.state.decision.intent}"',
            "",
        ]

        if ctx.state.email_result is not None:
            er = ctx.state.email_result
            lines += [
                "[EMAILS]",
                f"Processed: {er.processed} | Actionable: {er.actionable} | Pending drafts: {len(er.pending_ids)}",
                "",
            ]

        if ctx.state.calendar_result is not None:
            cr = ctx.state.calendar_result
            lines += [
                "[CALENDAR]",
                f"Date: {cr.date} | Total events: {cr.total_events} | Conflicts: {len(cr.conflicts)}",
                f"Summary: {cr.summary}",
                "",
            ]

        if ctx.state.email_result is None and ctx.state.calendar_result is None:
            log.warning("SynthesizeNode  →  no pipeline results available, synthesizing from query alone")
            lines.append("No data was retrieved from any pipeline.")

        context = "\n".join(lines)
        synthesis = await synthesize_agent.run(context)
        log.info("SynthesizeNode  →  synthesis complete")

        return End(OrchestratorResult(
            summary=synthesis.output,
            email_result=ctx.state.email_result,
            calendar_result=ctx.state.calendar_result,
        ))


with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    planner_graph = Graph(
        nodes=(PlannerNode, ClarifyNode, EmailPipelineNode, CalendarPipelineNode, SynthesizeNode),
        state_type=OrchestratorState,
    )


async def run_orchestrator_pipeline(query: str) -> OrchestratorResult:
    log.info("=== Orchestrator pipeline START  query=%r ===", query)
    state = OrchestratorState(query=query)
    result = await planner_graph.run(PlannerNode(), state=state)
    log.info("=== Orchestrator pipeline END ===")
    return result.output
