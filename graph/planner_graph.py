import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
import os

from pydantic_ai import UsageLimits

from agents.manager_agent import manager_agent
from graph.session_store import session_store
from models.calendar_models import CalendarActionResult
from models.email_models import ProcessingResult
from models.orchestrator_models import ManagerOutput, OrchestratorResult, WorkdayDeps, WorkdayMemory
from config.logger import get_logger, log_agent_run
from utils.graph_utils import get_session_lock

log = get_logger("workday_pipeline")


async def run_orchestrator_pipeline(query: str, session_id: str | None = None) -> OrchestratorResult:
    session_id = session_id or str(uuid.uuid4())
    lock = await get_session_lock(session_id)
    async with lock:
        log.info("=== Pipeline START  query=%r  session=%r ===", query, session_id)

        tz_name = os.environ.get("USER_TIMEZONE", "Asia/Kolkata")
        user_tz = ZoneInfo(tz_name)
        now_local = datetime.now(user_tz)
        now_unix = int(now_local.timestamp())
        now_label = now_local.strftime("%A %Y-%m-%d %I:%M %p")

        h = await session_store.get_unified(session_id)

        working_memory = WorkdayMemory(recent_events=list(h.recent_events))
        deps = WorkdayDeps(
            user_tz=tz_name,
            now_unix=now_unix,
            now_label=now_label,
            working_memory=working_memory,
            calendar_history=list(h.calendar_action),
        )

        output_obj = None
        new_manager_msgs = []
        try:
            result = await manager_agent.run(
                query,
                deps=deps,
                message_history=list(h.manager),
                usage_limits=UsageLimits(request_limit=20),
            )
            log_agent_run(log, result)
            output_obj = result.output
            if isinstance(output_obj, str):
                output_obj = ManagerOutput(summary=output_obj)
            new_manager_msgs = result.new_messages()
        except Exception as exc:
            log.error("=== Pipeline FAILED  query=%r: %s ===", query, exc, exc_info=True)
            output_obj = None

        wm = deps.working_memory

        email_result: ProcessingResult | None = None
        if wm.email_pending_ids:
            email_result = ProcessingResult(
                processed=0,
                actionable=len(wm.email_pending_ids),
                pending_ids=wm.email_pending_ids,
            )

        calendar_action_result: CalendarActionResult | None = None
        if output_obj is not None and wm.calendar_changed:
            calendar_action_result = CalendarActionResult(
                description=output_obj.summary,
                executed=True,
                awaiting_user=False,
            )
        elif output_obj is not None:
            calendar_action_result = CalendarActionResult(
                description=output_obj.summary,
                executed=False,
                awaiting_user=False,
            )

        calendar_action_open = False
        if output_obj is not None and output_obj.clarification_question:
            calendar_action_open = h.calendar_action_open

        merged_manager = list(h.manager) + new_manager_msgs
        await session_store.save_unified(
            session_id=session_id,
            manager_msgs=merged_manager,
            calendar_msgs=deps.calendar_history,
            recent_events=wm.recent_events,
            calendar_action_open=calendar_action_open,
        )

        log.info(
            "=== Pipeline END  session=%r  manager_h=%d  cal_h=%d  events=%d ===",
            session_id,
            len(merged_manager),
            len(deps.calendar_history),
            len(wm.recent_events),
        )

        if output_obj is None:
            summary = "Something went wrong while handling that. Please try again."
            clarification_question = None
        else:
            summary = output_obj.summary
            clarification_question = output_obj.clarification_question

        result_obj = OrchestratorResult(
            summary=summary,
            session_id=session_id,
            email_result=email_result,
            calendar_action_result=calendar_action_result,
            clarification_question=clarification_question,
        )
        return result_obj
