import re
import warnings
from dataclasses import dataclass

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from pydantic_graph import BaseNode, End, Graph, GraphRunContext

from agents.planner_agent import planner_agent
from agents.synthesize_agent import synthesize_agent
from agents.calendar_agent import calendar_agent
from agents.email_node import email_node_agent
from graph.pending_store import pending_store
from models.orchestrator_models import AgentDecision, OrchestratorResult, OrchestratorState
from models.email_models import ProcessingResult
from services.calendar_service import fetch_calendar_data
from utils.calendar_utils import build_calendar_prompt
from config.logger import get_logger

log = get_logger("workday_graph")

_BODY_CHAR_LIMIT = 2000


def _clean_body(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:_BODY_CHAR_LIMIT]


@dataclass
class PlannerNode(BaseNode[OrchestratorState]):
    async def run(
        self, ctx: GraphRunContext[OrchestratorState]
    ) -> "ClarifyNode | FetchEmailsNode | FetchCalendarNode | SynthesizeNode":
        log.info("PlannerNode  →  running planner_agent on query: %r", ctx.state.query)
        result = await planner_agent.run(ctx.state.query)
        ctx.state.decision = result.output
        decision = ctx.state.decision
        log.info(
            "PlannerNode  →  decision: intent=%r  next_node=%r  needs_email=%s  needs_calendar=%s",
            decision.intent, decision.next_node, decision.needs_email, decision.needs_calendar,
        )

        _node_map: dict[str, type] = {
            "FetchEmailsNode": FetchEmailsNode,
            "FetchCalendarNode": FetchCalendarNode,
            "ClarifyNode": ClarifyNode,
            "SynthesizeNode": SynthesizeNode,
        }
        node_cls = _node_map.get(decision.next_node)
        if node_cls is None:
            log.warning("PlannerNode  →  unknown next_node %r, falling back to SynthesizeNode", decision.next_node)
            node_cls = SynthesizeNode
        log.info("PlannerNode  →  routing to %s", node_cls.__name__)
        return node_cls()


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
class FetchEmailsNode(BaseNode[OrchestratorState]):
    n: int = 10

    async def run(self, ctx: GraphRunContext[OrchestratorState]) -> "ClassifyNode":
        log.info("FetchEmailsNode  →  fetching up to %d emails", self.n)
        from tools.email_tools import list_emails
        ctx.state.emails = await list_emails(self.n)
        ctx.state.current_index = 0
        log.info("FetchEmailsNode  →  fetched %d emails", len(ctx.state.emails))
        return ClassifyNode()


@dataclass
class ClassifyNode(BaseNode[OrchestratorState]):
    async def run(
        self, ctx: GraphRunContext[OrchestratorState]
    ) -> "DraftNode | BuildEmailResultNode":
        idx = ctx.state.current_index
        total = len(ctx.state.emails)

        if idx >= total:
            log.info(
                "ClassifyNode  →  all %d emails processed → BuildEmailResultNode  (actionable=%d)",
                total, len(ctx.state.pending_ids),
            )
            return BuildEmailResultNode()

        email = ctx.state.emails[idx]
        log.info("ClassifyNode  →  [%d/%d] subject=%r  from=%r", idx + 1, total, email.subject, email.sender)

        if pending_store.has_email(email.id):
            log.debug("ClassifyNode  →  email %r already in pending store, skipping", email.id)
            ctx.state.current_index += 1
            return ClassifyNode()

        from tools.email_tools import fetch_email_body
        log.debug("ClassifyNode  →  fetching body for email %r", email.id)
        body = _clean_body(await fetch_email_body(email.id))
        log.debug("ClassifyNode  →  running email_node_agent")
        result = await email_node_agent.run(
            f"Email ID: {email.id}\nFrom: {email.sender}\n"
            f"Subject: {email.subject}\nDate: {email.date}\nBody:\n{body}"
        )
        output = result.output
        output.email_id = email.id
        output.subject = email.subject
        output.sender = email.sender
        if output.draft is not None:
            output.draft.to = email.sender
        ctx.state.email_outputs.append(output)
        log.info(
            "ClassifyNode  →  classified as %r  (draft=%s)",
            output.classification.label, output.draft is not None,
        )
        return DraftNode()


@dataclass
class DraftNode(BaseNode[OrchestratorState]):
    async def run(self, ctx: GraphRunContext[OrchestratorState]) -> "HumanGateNode | ClassifyNode":
        output = ctx.state.email_outputs[-1]
        if output.classification.label == "actionable" and output.draft is not None:
            log.info("DraftNode  →  email is actionable with draft → routing to HumanGateNode")
            return HumanGateNode()
        log.debug("DraftNode  →  not actionable or no draft, moving to next email")
        ctx.state.current_index += 1
        return ClassifyNode()


@dataclass
class HumanGateNode(BaseNode[OrchestratorState]):
    async def run(self, ctx: GraphRunContext[OrchestratorState]) -> "ClassifyNode":
        output = ctx.state.email_outputs[-1]
        pending_id = pending_store.add(output)
        ctx.state.pending_ids.append(pending_id)
        log.info("HumanGateNode  →  stored pending draft  id=%r  subject=%r", pending_id, output.subject)
        ctx.state.current_index += 1
        return ClassifyNode()


@dataclass
class BuildEmailResultNode(BaseNode[OrchestratorState]):
    async def run(
        self, ctx: GraphRunContext[OrchestratorState]
    ) -> "FetchCalendarNode | SynthesizeNode":
        total = len(ctx.state.emails)
        ctx.state.email_result = ProcessingResult(
            processed=total,
            actionable=len(ctx.state.pending_ids),
            pending_ids=ctx.state.pending_ids,
        )
        log.info(
            "BuildEmailResultNode  →  email result built: processed=%d  actionable=%d  pending=%d",
            total, len(ctx.state.pending_ids), len(ctx.state.pending_ids),
        )
        if ctx.state.decision.needs_calendar:
            log.info("BuildEmailResultNode  →  calendar needed, routing to FetchCalendarNode")
            return FetchCalendarNode()
        log.info("BuildEmailResultNode  →  routing to SynthesizeNode")
        return SynthesizeNode()


@dataclass
class FetchCalendarNode(BaseNode[OrchestratorState]):
    async def run(self, ctx: GraphRunContext[OrchestratorState]) -> "CalendarNode":
        log.info("FetchCalendarNode  →  fetching calendar data")
        ctx.state.events, ctx.state.conflicts, ctx.state.date_str = await fetch_calendar_data()
        log.info(
            "FetchCalendarNode  →  fetched %d events, %d conflicts for %s",
            len(ctx.state.events), len(ctx.state.conflicts), ctx.state.date_str,
        )
        return CalendarNode()


@dataclass
class CalendarNode(BaseNode[OrchestratorState]):
    async def run(self, ctx: GraphRunContext[OrchestratorState]) -> "SynthesizeNode":
        log.info("CalendarNode  →  running calendar_agent on %d events", len(ctx.state.events))
        prompt = build_calendar_prompt(ctx.state.events, ctx.state.conflicts, ctx.state.date_str)
        result = await calendar_agent.run(prompt)
        output = result.output
        output.date = ctx.state.date_str
        output.total_events = len(ctx.state.events)
        output.conflicts = ctx.state.conflicts
        ctx.state.calendar_result = output
        log.info("CalendarNode  →  analysis done: %d suggestions", len(output.suggestions))
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
    workday_graph = Graph(
        nodes=(
            PlannerNode,
            ClarifyNode,
            FetchEmailsNode,
            ClassifyNode,
            DraftNode,
            HumanGateNode,
            BuildEmailResultNode,
            FetchCalendarNode,
            CalendarNode,
            SynthesizeNode,
        ),
        state_type=OrchestratorState,
    )


async def run_orchestrator_pipeline(query: str) -> OrchestratorResult:
    log.info("=== Workday pipeline START  query=%r ===", query)
    state = OrchestratorState(query=query)
    result = await workday_graph.run(PlannerNode(), state=state)
    log.info("=== Workday pipeline END ===")
    return result.output
