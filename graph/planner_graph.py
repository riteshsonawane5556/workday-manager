import re
import warnings
from dataclasses import dataclass

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from pydantic_graph import BaseNode, End, Graph, GraphRunContext

from agents.planner_agent import planner_agent
from agents.synthesize_agent import synthesize_agent
from agents.calendar_action_agent import calendar_action_agent
from agents.email_node import email_node_agent
from graph.pending_store import pending_store
from models.orchestrator_models import AgentDecision, OrchestratorResult, OrchestratorState
from models.email_models import ProcessingResult
from config.logger import get_logger, log_agent_run

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
    ) -> "ClarifyNode | FetchEmailsNode | CalendarActionNode | SynthesizeNode":
        log.info("PlannerNode  ->  running planner_agent on query: %r", ctx.state.query)
        if ctx.state.calendar_action_open:
            planner_prompt = (
                "[A calendar action conversation is currently open and waiting for the user's "
                "reply. This message is the user's reply continuing it - route to "
                "'CalendarActionNode'.]\n"
                f"User: {ctx.state.query}"
            )
        else:
            planner_prompt = ctx.state.query
        result = await planner_agent.run(
            planner_prompt,
            message_history=ctx.state.planner_history,
        )
        log_agent_run(log, result)
        ctx.state.planner_history += result.new_messages()
        ctx.state.decision = result.output
        decision = ctx.state.decision
        log.info(
            "PlannerNode  ->  decision: intent=%r  next_node=%r  needs_email=%s  needs_calendar=%s",
            decision.intent, decision.next_node, decision.needs_email, decision.needs_calendar,
        )

        _node_map: dict[str, type] = {
            "FetchEmailsNode": FetchEmailsNode,
            "CalendarActionNode": CalendarActionNode,
            "ClarifyNode": ClarifyNode,
            "SynthesizeNode": SynthesizeNode,
        }
        node_cls = _node_map.get(decision.next_node)
        if node_cls is None:
            log.warning("PlannerNode  ->  unknown next_node %r, falling back to SynthesizeNode", decision.next_node)
            node_cls = SynthesizeNode
        log.info("PlannerNode  ->  routing to %s", node_cls.__name__)
        return node_cls()


@dataclass
class ClarifyNode(BaseNode[OrchestratorState]):
    async def run(self, ctx: GraphRunContext[OrchestratorState]) -> End[OrchestratorResult]:
        log.info("ClarifyNode  ->  query is ambiguous, returning clarification question")
        question = ctx.state.decision.clarification_question or "Could you clarify what you need help with?"
        return End(OrchestratorResult(
            summary=question,
            clarification_question=question,
        ))


@dataclass
class FetchEmailsNode(BaseNode[OrchestratorState]):
    n: int = 10

    async def run(self, ctx: GraphRunContext[OrchestratorState]) -> "ClassifyNode":
        log.info("FetchEmailsNode  ->  fetching up to %d emails", self.n)
        from tools.email_tools import list_emails
        ctx.state.emails = await list_emails(self.n)
        ctx.state.current_index = 0
        log.info("FetchEmailsNode  ->  fetched %d emails", len(ctx.state.emails))
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
                "ClassifyNode  ->  all %d emails processed -> BuildEmailResultNode  (actionable=%d)",
                total, len(ctx.state.pending_ids),
            )
            return BuildEmailResultNode()

        email = ctx.state.emails[idx]
        log.info("ClassifyNode  ->  [%d/%d] subject=%r  from=%r", idx + 1, total, email.subject, email.sender)

        if pending_store.has_email(email.id):
            log.debug("ClassifyNode  ->  email %r already in pending store, skipping", email.id)
            ctx.state.current_index += 1
            return ClassifyNode()

        from tools.email_tools import fetch_email_body
        log.debug("ClassifyNode  ->  fetching body for email %r", email.id)
        body = _clean_body(await fetch_email_body(email.id))
        log.debug("ClassifyNode  ->  running email_node_agent")
        result = await email_node_agent.run(
            f"Email ID: {email.id}\nFrom: {email.sender}\n"
            f"Subject: {email.subject}\nDate: {email.date}\nBody:\n{body}"
        )
        log_agent_run(log, result)
        output = result.output
        output.email_id = email.id
        output.subject = email.subject
        output.sender = email.sender
        if output.draft is not None:
            output.draft.to = email.sender
        ctx.state.email_outputs.append(output)
        log.info(
            "ClassifyNode  ->  classified as %r  (draft=%s)",
            output.classification.label, output.draft is not None,
        )
        return DraftNode()


@dataclass
class DraftNode(BaseNode[OrchestratorState]):
    async def run(self, ctx: GraphRunContext[OrchestratorState]) -> "HumanGateNode | ClassifyNode":
        output = ctx.state.email_outputs[-1]
        if output.classification.label == "actionable" and output.draft is not None:
            log.info("DraftNode  ->  email is actionable with draft -> routing to HumanGateNode")
            return HumanGateNode()
        log.debug("DraftNode  ->  not actionable or no draft, moving to next email")
        ctx.state.current_index += 1
        return ClassifyNode()


@dataclass
class HumanGateNode(BaseNode[OrchestratorState]):
    async def run(self, ctx: GraphRunContext[OrchestratorState]) -> "ClassifyNode":
        output = ctx.state.email_outputs[-1]
        pending_id = pending_store.add(output)
        ctx.state.pending_ids.append(pending_id)
        log.info("HumanGateNode  ->  stored pending draft  id=%r  subject=%r", pending_id, output.subject)
        ctx.state.current_index += 1
        return ClassifyNode()


@dataclass
class BuildEmailResultNode(BaseNode[OrchestratorState]):
    async def run(
        self, ctx: GraphRunContext[OrchestratorState]
    ) -> "CalendarActionNode | SynthesizeNode":
        total = len(ctx.state.emails)
        ctx.state.email_result = ProcessingResult(
            processed=total,
            actionable=len(ctx.state.pending_ids),
            pending_ids=ctx.state.pending_ids,
        )
        log.info(
            "BuildEmailResultNode  ->  email result built: processed=%d  actionable=%d  pending=%d",
            total, len(ctx.state.pending_ids), len(ctx.state.pending_ids),
        )
        if ctx.state.decision.needs_calendar:
            log.info("BuildEmailResultNode  ->  calendar needed, routing to CalendarActionNode")
            return CalendarActionNode()
        log.info("BuildEmailResultNode  ->  routing to SynthesizeNode")
        return SynthesizeNode()


@dataclass
class CalendarActionNode(BaseNode[OrchestratorState]):
    async def run(self, ctx: GraphRunContext[OrchestratorState]) -> "SynthesizeNode":
        import os
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from models.calendar_models import CalendarActionResult, CalendarDeps

        tz_name = os.environ.get("USER_TIMEZONE", "Asia/Kolkata")
        user_tz = ZoneInfo(tz_name)
        now_local = datetime.now(user_tz)
        now_unix = int(now_local.timestamp())
        now_label = now_local.strftime("%A %Y-%m-%d %I:%M %p")

        day_overview = ctx.state.decision.needs_email and ctx.state.decision.needs_calendar
        deps = CalendarDeps(user_tz=tz_name, now_unix=now_unix, now_label=now_label)
        if day_overview:
            request = (
                "Give a read-only summary of today's calendar as part of a full day briefing: call "
                "get_events and check_conflicts, then describe today's schedule and flag any conflicts. "
                "Do NOT create, change, or cancel anything and do NOT ask a follow-up question."
            )
        else:
            request = ctx.state.query
        prompt = (
            f"Current local date and time: {now_label} ({tz_name}). Today is day_offset=0.\n"
            f"User request: {request}"
        )

        log.info(
            "CalendarActionNode  ->  running agentic calendar_action_agent  now=%s  day_overview=%s",
            now_label, day_overview,
        )
        result = await calendar_action_agent.run(
            prompt,
            deps=deps,
            message_history=ctx.state.calendar_action_history,
        )
        log_agent_run(log, result)
        ctx.state.calendar_action_history += result.new_messages()
        reply = result.output
        changed = deps.changed_calendar
        awaiting_user = (not changed) and not day_overview
        log.info(
            "CalendarActionNode  ->  changed_calendar=%s  awaiting_user=%s  reply=%r",
            changed, awaiting_user, reply,
        )

        ctx.state.calendar_action_result = CalendarActionResult(
            description=reply,
            executed=changed,
            awaiting_user=awaiting_user,
        )
        return SynthesizeNode()


@dataclass
class SynthesizeNode(BaseNode[OrchestratorState]):
    async def run(self, ctx: GraphRunContext[OrchestratorState]) -> End[OrchestratorResult]:
        log.info("SynthesizeNode  ->  running synthesize_agent")
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
            ]
            for o in ctx.state.email_outputs:
                draft_note = " (draft reply ready)" if o.draft is not None else ""
                lines.append(
                    f"  - [{o.classification.label.upper()}] {o.subject!r} from {o.sender}{draft_note}"
                )
            lines.append("")

        if ctx.state.calendar_action_result is not None:
            car = ctx.state.calendar_action_result
            if car.awaiting_user:
                log.info("SynthesizeNode  ->  calendar agent awaiting user, returning its reply directly")
                return End(OrchestratorResult(
                    summary=car.description,
                    calendar_action_result=car,
                    clarification_question=car.description,
                ))
            status = "Calendar changed" if car.executed else "No change made"
            lines += [
                "[CALENDAR ACTION]",
                f"{car.description}",
                f"Status: {status}",
                "",
            ]

        if ctx.state.email_result is None and ctx.state.calendar_action_result is None:
            log.warning("SynthesizeNode  ->  no pipeline results available, synthesizing from query alone")
            lines.append("No data was retrieved from any pipeline.")

        context = "\n".join(lines)
        synthesis = await synthesize_agent.run(
            context,
            message_history=ctx.state.synthesize_history,
        )
        log_agent_run(log, synthesis)
        ctx.state.synthesize_history += synthesis.new_messages()
        log.info("SynthesizeNode  ->  synthesis complete")

        return End(OrchestratorResult(
            summary=synthesis.output,
            email_result=ctx.state.email_result,
            calendar_action_result=ctx.state.calendar_action_result,
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
            CalendarActionNode,
            SynthesizeNode,
        ),
        state_type=OrchestratorState,
    )

print("code->", workday_graph.mermaid_code())

async def run_orchestrator_pipeline(query: str, session_id: str = "default") -> OrchestratorResult:
    from graph.session_store import session_store, SessionHistory
    log.info("=== Workday pipeline START  query=%r  session=%r ===", query, session_id)
    h = session_store.get(session_id)
    state = OrchestratorState(
        query=query,
        planner_history=list(h.planner),
        calendar_action_history=list(h.calendar_action),
        synthesize_history=list(h.synthesize),
        calendar_action_open=h.calendar_action_open,
    )
    result = await workday_graph.run(PlannerNode(), state=state)

    car = state.calendar_action_result
    calendar_action_open = bool(car is not None and car.awaiting_user)

    session_store.set(session_id, SessionHistory(
        planner=state.planner_history,
        calendar_action=state.calendar_action_history if calendar_action_open else [],
        synthesize=state.synthesize_history,
        calendar_action_open=calendar_action_open,
    ))
    log.info(
        "=== Workday pipeline END  planner_h=%d  cal_action_h=%d  synth_h=%d  cal_open=%s ===",
        len(state.planner_history), len(state.calendar_action_history),
        len(state.synthesize_history), calendar_action_open,
    )
    return result.output
