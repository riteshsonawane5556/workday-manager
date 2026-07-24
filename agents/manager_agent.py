import os
from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic_ai import Agent, RunContext

from agents.calendar_action_agent import calendar_action_agent
from agents.compose_agent import compose_agent
from config.logger import get_logger
from models.calendar_models import CalendarDeps
from models.orchestrator_models import ManagerOutput, RecentEvent, WorkdayDeps

log = get_logger("manager_agent")

manager_agent = Agent(
    "groq:openai/gpt-oss-120b",
    deps_type=WorkdayDeps,
    output_type=ManagerOutput | str,
    retries=3,
    instructions=(
        "You are a workday manager agent. Your job is to handle the user's request by calling the "
        "right specialist tools, then summarizing the outcome.\n\n"
        "AVAILABLE TOOLS:\n"
        "  - manage_calendar: any calendar request — read schedule, book, reschedule, cancel, check conflicts\n"
        "  - triage_inbox: read inbox, classify emails, draft replies for actionable emails\n"
        "  - compose_email: send a brand-new outbound email (not a reply to existing inbox)\n"
        "  - send_meeting_invitation: invite someone to a scheduled meeting AND send them an email about it\n\n"
        "SEQUENCING RULES:\n"
        "  1. When asked to schedule a meeting AND notify/invite someone: FIRST call manage_calendar to "
        "create the event and get real event details, THEN call send_meeting_invitation with the "
        "attendee email and event_id from the result. Never compose an email about a meeting you have "
        "not yet created.\n"
        "  2. When asked to send a mail about 'the meeting' or 'the meet scheduled above': check the "
        "[RECENT EVENTS] context injected in your instructions. If a recent event matches, call "
        "compose_email or send_meeting_invitation with those real details.\n"
        "  3. For a day overview (plan my day / how is my day looking): call both triage_inbox AND "
        "manage_calendar, then summarize together.\n"
        "  4. For pure calendar requests (show schedule, book, reschedule, cancel): call manage_calendar only.\n"
        "  5. For pure email requests (check inbox, reply to emails): call triage_inbox only.\n"
        "  6. For composing a new email to someone: call compose_email.\n"
        "  7. For greetings, small talk, or meta questions: reply directly without calling any tool.\n"
        "  8. If the request is ambiguous and names no domain, set clarification_question.\n\n"
        "NEVER describe or confirm an action you have not taken via a tool call. "
        "After tool calls, summarize results concisely."
    ),
)


@manager_agent.instructions
def _context_hint(ctx: RunContext[WorkdayDeps]) -> str:
    d = ctx.deps
    lines = [
        f"Current local time: {d.now_label} (timezone: {d.user_tz}). Today is day_offset=0.",
    ]
    if d.working_memory.recent_events:
        lines.append("\n[RECENT EVENTS from this session]")
        tz = ZoneInfo(d.user_tz)
        for e in d.working_memory.recent_events[-5:]:
            start = datetime.fromtimestamp(e.start_unix, tz=tz).strftime("%a %b %d, %I:%M %p")
            end = datetime.fromtimestamp(e.end_unix, tz=tz).strftime("%I:%M %p")
            attendees = ", ".join(e.attendees) if e.attendees else "none"
            lines.append(f"  - id={e.id} | {e.title!r} | {start}–{end} | attendees: {attendees}")
    return "\n".join(lines)


@manager_agent.tool
async def manage_calendar(ctx: RunContext[WorkdayDeps], request: str) -> str:
    """Delegate a calendar request (read, book, reschedule, cancel, conflict check) to the calendar specialist."""
    deps = CalendarDeps(
        user_tz=ctx.deps.user_tz,
        now_unix=ctx.deps.now_unix,
        now_label=ctx.deps.now_label,
        sink=ctx.deps.working_memory,
    )
    prompt = (
        f"Current local date and time: {ctx.deps.now_label} ({ctx.deps.user_tz}). "
        f"Today is day_offset=0.\nUser request: {request}"
    )
    log.info("manage_calendar tool -> delegating: %r", request)
    result = await calendar_action_agent.run(
        prompt,
        deps=deps,
        message_history=ctx.deps.calendar_history,
        usage=ctx.usage,
    )
    ctx.deps.calendar_history += result.new_messages()
    if deps.changed_calendar:
        ctx.deps.working_memory.calendar_changed = True
    log.info("manage_calendar tool -> done, changed=%s", deps.changed_calendar)
    return result.output


@manager_agent.tool
async def triage_inbox(ctx: RunContext[WorkdayDeps], limit: int = 10) -> str:
    """Triage the inbox: classify emails and draft replies for actionable ones."""
    from services.inbox_service import run_inbox_triage
    log.info("triage_inbox tool -> running inbox triage limit=%d", limit)
    summary, pending_ids = await run_inbox_triage(limit)
    ctx.deps.working_memory.email_pending_ids.extend(pending_ids)
    log.info("triage_inbox tool -> done, pending_ids=%s", pending_ids)
    return summary


@manager_agent.tool
async def compose_email(ctx: RunContext[WorkdayDeps], to: str, subject: str, body: str) -> str:
    """Stage a new outbound email for human approval. Returns a confirmation with the pending id."""
    if not to or "@" not in to:
        return "NO_RECIPIENT: please provide a valid email address."
    from services.inbox_service import stage_outbound_draft
    log.info("compose_email tool -> staging draft to=%r subject=%r", to, subject)
    pid = await stage_outbound_draft(to=to, subject=subject, body=body)
    ctx.deps.working_memory.email_pending_ids.append(pid)
    log.info("compose_email tool -> staged as pending id=%r", pid)
    return f"Email to {to!r} staged for approval (id={pid}). It will be sent after you approve it."


@manager_agent.tool
async def send_meeting_invitation(
    ctx: RunContext[WorkdayDeps],
    attendee_email: str,
    event_id: str | None = None,
    note: str | None = None,
) -> str:
    """Invite someone to a meeting: adds them to the calendar event (real Nylas invite) AND stages an email about the meeting for approval."""
    if not attendee_email or "@" not in attendee_email:
        return "NO_RECIPIENT: please provide a valid attendee email address."

    tz = ZoneInfo(ctx.deps.user_tz)

    target_event: RecentEvent | None = None
    if event_id:
        target_event = next(
            (e for e in ctx.deps.working_memory.recent_events if e.id == event_id), None
        )
    if target_event is None and ctx.deps.working_memory.recent_events:
        target_event = ctx.deps.working_memory.recent_events[-1]

    invite_result = "No event found to add attendee to."
    if target_event:
        from tools.calendar_tools import add_participant
        try:
            added = await add_participant(target_event.id, attendee_email)
            if added:
                invite_result = f"Added {attendee_email} to event '{target_event.title}' and sent calendar invite."
                if attendee_email not in target_event.attendees:
                    target_event.attendees.append(attendee_email)
            else:
                invite_result = f"{attendee_email} is already a participant in '{target_event.title}'."
            ctx.deps.working_memory.calendar_changed = True
        except Exception as exc:
            log.error("send_meeting_invitation -> add_participant failed: %s", exc)
            invite_result = f"Could not add to calendar event: {exc}"

    email_result = "No email staged."
    if target_event:
        start = datetime.fromtimestamp(target_event.start_unix, tz=tz).strftime("%A %B %d, %I:%M %p")
        end = datetime.fromtimestamp(target_event.end_unix, tz=tz).strftime("%I:%M %p")
        duration_mins = (target_event.end_unix - target_event.start_unix) // 60
        additional_note = f"\n\nNote: {note}" if note else ""
        compose_instruction = (
            f"Write a professional meeting invitation email to {attendee_email} for a meeting titled "
            f"'{target_event.title}' scheduled on {start}–{end} ({duration_mins} minutes).{additional_note} "
            f"Confirm the meeting details and ask them to let you know if they have any questions."
        )
        try:
            draft_result = await compose_agent.run(compose_instruction, usage=ctx.usage)
            draft = draft_result.output
            draft.to = attendee_email
            from services.inbox_service import stage_outbound_draft
            pid = await stage_outbound_draft(to=attendee_email, subject=draft.subject, body=draft.body)
            ctx.deps.working_memory.email_pending_ids.append(pid)
            email_result = f"Email about the meeting staged for your approval (id={pid})."
            log.info("send_meeting_invitation -> email staged id=%r to=%r", pid, attendee_email)
        except Exception as exc:
            log.error("send_meeting_invitation -> compose failed: %s", exc)
            email_result = f"Could not draft invitation email: {exc}"
    else:
        email_result = "No recent event found to reference in the email."

    return f"{invite_result} {email_result}"
