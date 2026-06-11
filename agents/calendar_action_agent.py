from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic_ai import Agent, RunContext

from config.logger import get_logger
from models.calendar_models import CalendarDeps, ConflictPair
from tools.calendar_tools import (
    clock_to_unix,
    create_event as create_event_tool,
    delete_event as delete_event_tool,
    fetch_today_events,
    update_event as update_event_tool,
)

log = get_logger("calendar_action_agent")

calendar_action_agent = Agent(
    "groq:openai/gpt-oss-120b",
    deps_type=CalendarDeps,
    output_type=str,
    retries=3,
    system_prompt=(
        "You are a calendar assistant that books, reschedules, updates and cancels events on the "
        "user's behalf BY CALLING TOOLS. You reason over tool results - no external logic guides you.\n\n"
        "CRITICAL: Never say a meeting is booked, moved, or cancelled unless you have actually called "
        "the matching tool and it returned a success line. Do NOT narrate intentions like 'I will check "
        "the calendar' or 'I will book it' - actually CALL the tool in this same turn, then report the "
        "real result. If you have enough information to act, the correct response is a tool call, not a "
        "sentence describing what you are about to do.\n\n"
        "TIME HANDLING:\n"
        "  - Each run you are given the current local date and time in the user's timezone.\n"
        "  - You never compute Unix timestamps. When you call create_event or update_event you pass "
        "plain wall-clock parts and the tool converts them exactly: day_offset (0 = today, 1 = "
        "tomorrow, 2 = day after, ...), hour in 24-hour form (e.g. 6pm -> 18, 9am -> 9), minute (0-59), "
        "and duration_minutes.\n"
        "  - A bare time like '3pm' means today (day_offset=0) unless the user clearly means another "
        "day. Convert 12-hour to 24-hour: 12am -> 0, 12pm -> 12, 1pm -> 13, ... 11pm -> 23.\n"
        "  - If a requested time today has already passed (compare against the current time you were "
        "given), ask whether to book it for tomorrow instead rather than silently shifting it.\n"
        "  - Default duration_minutes is 30 when unspecified.\n\n"
        "CONFLICTS:\n"
        "  - When the user asks about clashes, double-bookings, or 'what conflicts do I have', call "
        "get_events then check_conflicts and report each overlapping pair in plain language. If "
        "check_conflicts reports none, say the day is clash-free.\n"
        "  - When you list the day's schedule, also call check_conflicts and proactively mention any "
        "overlaps you find - do not make the user ask.\n"
        "  - Before booking or rescheduling into a slot, you can call check_conflicts to confirm the "
        "slot is free. If a clash exists, describe it and ask whether to book anyway (see WORKFLOW).\n"
        "  - To resolve a conflict, suggest moving the shorter event to a nearby free slot on the same "
        "day, then make the change only after the user confirms (it is an UPDATE - confirm first).\n\n"
        "WORKFLOW (every turn):\n"
        "  1. Call get_events first to see what is already scheduled.\n"
        "  2. CREATE: you need a title, a start time and duration. If either is missing, ask ONE concise question "
        "for exactly the missing piece - never invent a title or time. If a different event overlaps the "
        "requested slot, do NOT create yet: describe the clash and ask whether to book anyway; call "
        "create_event only if the user confirms (e.g. 'yes', 'book it anyway'). If the slot is free and "
        "you have title + time, call create_event immediately - no approval needed.\n"
        "  3. UPDATE / RESCHEDULE / DELETE change existing data, so confirm first. Identify the exact "
        "event from get_events (match by title/time); if ambiguous, ask which one. State precisely what "
        "you will change and ask the user to confirm. Call update_event/delete_event only after they "
        "confirm.\n\n"
        "PARTICIPANTS: only pass emails the user explicitly gave that look real (contain '@' and a "
        "domain). Never invent or guess an address, and never use a name as an email. No attendees "
        "given -> pass an empty list.\n\n"
        "BARE CONFIRMATIONS: a short reply like 'yes', 'ok', or 'book it anyway' is ONLY meaningful as "
        "an answer to a question you asked on the previous turn. If there is no pending action in the "
        "conversation that such a reply would confirm, do NOT create or change anything - instead ask "
        "what they would like to schedule. Never invent a title (e.g. 'Unknown') or a time to satisfy a "
        "bare 'yes'.\n\n"
        "REPLYING: after your tool calls, reply in one short, natural sentence. If you changed the "
        "calendar, confirm exactly what changed (title and time). If you are waiting on the user, end "
        "with a clear question. Carry context across turns: a short reply like 'yes', '3pm', or 'call it "
        "Standup' continues the previous request - combine it with what was already established."
        
    ),
)


@calendar_action_agent.tool
async def get_events(ctx: RunContext[CalendarDeps]) -> str:
    """Return all calendar events scheduled for today with times and attendees."""
    tz = ZoneInfo(ctx.deps.user_tz)
    events = await fetch_today_events()
    if not events:
        return "No events scheduled today."
    lines = []
    for e in events:
        s = datetime.fromtimestamp(e.start_time, tz=tz).strftime("%I:%M %p")
        en = datetime.fromtimestamp(e.end_time, tz=tz).strftime("%I:%M %p")
        attendees = ", ".join(e.participants) if e.participants else "none"
        lines.append(
            f"id={e.id} | title={e.title!r} | {s}-{en} "
            f"| start_unix={e.start_time} | end_unix={e.end_time} | attendees={attendees}"
        )
    log.info("get_events tool -> returned %d events", len(events))
    return "Events today:\n" + "\n".join(lines)


@calendar_action_agent.tool
async def check_conflicts(ctx: RunContext[CalendarDeps]) -> str:
    """Detect and report all overlapping event pairs on today's calendar."""
    tz = ZoneInfo(ctx.deps.user_tz)
    events = await fetch_today_events()
    ordered = sorted(events, key=lambda e: e.start_time)
    conflicts: list[ConflictPair] = []
    for i in range(len(ordered)):
        for j in range(i + 1, len(ordered)):
            a, b = ordered[i], ordered[j]
            if a.start_time < b.end_time and a.end_time > b.start_time:
                conflicts.append(ConflictPair(event_a=a, event_b=b))
    if not conflicts:
        log.info("check_conflicts tool -> no conflicts among %d events", len(events))
        return "No conflicts today."
    lines = []
    for c in conflicts:
        a, b = c.event_a, c.event_b
        a_s = datetime.fromtimestamp(a.start_time, tz=tz).strftime("%I:%M %p")
        a_e = datetime.fromtimestamp(a.end_time, tz=tz).strftime("%I:%M %p")
        b_s = datetime.fromtimestamp(b.start_time, tz=tz).strftime("%I:%M %p")
        b_e = datetime.fromtimestamp(b.end_time, tz=tz).strftime("%I:%M %p")
        lines.append(
            f"{a.title!r} ({a_s}-{a_e}, id={a.id}) overlaps "
            f"{b.title!r} ({b_s}-{b_e}, id={b.id})"
        )
    log.info("check_conflicts tool -> found %d conflict(s)", len(conflicts))
    return f"{len(conflicts)} conflict(s) today:\n" + "\n".join(lines)


@calendar_action_agent.tool
async def create_event(
    ctx: RunContext[CalendarDeps],
    title: str,
    day_offset: int,
    hour: int,
    minute: int = 0,
    duration_minutes: int = 30,
    participants: list[str] | None = None,
) -> str:
    """Create a new calendar event at the specified day/time offset with optional participants."""
    if not (0 <= hour <= 23) or not (0 <= minute <= 59):
        return f"Refused: hour must be 0-23 and minute 0-59 (got hour={hour}, minute={minute})."
    if duration_minutes <= 0:
        return f"Refused: duration_minutes must be positive (got {duration_minutes})."
    start_time = clock_to_unix(day_offset, hour, minute)
    end_time = start_time + duration_minutes * 60
    tz = ZoneInfo(ctx.deps.user_tz)
    when = datetime.fromtimestamp(start_time, tz=tz).strftime("%a %b %d, %I:%M %p")
    try:
        event_id = await create_event_tool(title, start_time, end_time, participants or [])
    except Exception as exc:
        log.error("create_event tool -> failed: %s", exc, exc_info=True)
        return f"Failed to create event: {exc}"
    ctx.deps.changed_calendar = True
    log.info("create_event tool -> created id=%r title=%r at %s", event_id, title, when)
    return f"Created event {title!r} on {when} (id={event_id})."


@calendar_action_agent.tool
async def update_event(
    ctx: RunContext[CalendarDeps],
    event_id: str,
    title: str | None = None,
    day_offset: int | None = None,
    hour: int | None = None,
    minute: int = 0,
    duration_minutes: int = 30,
    participants: list[str] | None = None,
) -> str:
    """Update title, time, duration, or participants of an existing event by its id."""
    if not event_id:
        return "Refused: event_id is required. Call get_events to find the correct id first."
    start_time: int | None = None
    end_time: int | None = None
    if day_offset is not None and hour is not None:
        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            return f"Refused: hour must be 0-23 and minute 0-59 (got hour={hour}, minute={minute})."
        if duration_minutes <= 0:
            return f"Refused: duration_minutes must be positive (got {duration_minutes})."
        start_time = clock_to_unix(day_offset, hour, minute)
        end_time = start_time + duration_minutes * 60
    elif (day_offset is None) != (hour is None):
        return "Refused: to change the time, provide both day_offset and hour."
    if title is None and start_time is None:
        return "Refused: nothing to update - provide a new title and/or a new time."
    try:
        await update_event_tool(event_id, title, start_time, end_time, participants)
    except Exception as exc:
        log.error("update_event tool -> failed: %s", exc, exc_info=True)
        return f"Failed to update event: {exc}"
    ctx.deps.changed_calendar = True
    log.info("update_event tool -> updated id=%r", event_id)
    return f"Updated event id={event_id}."


@calendar_action_agent.tool
async def delete_event(ctx: RunContext[CalendarDeps], event_id: str) -> str:
    """Permanently delete a calendar event by its id."""
    if not event_id:
        return "Refused: event_id is required. Call get_events to find the correct id first."
    try:
        await delete_event_tool(event_id)
    except Exception as exc:
        log.error("delete_event tool -> failed: %s", exc, exc_info=True)
        return f"Failed to delete event: {exc}"
    ctx.deps.changed_calendar = True
    log.info("delete_event tool -> deleted id=%r", event_id)
    return f"Deleted event id={event_id}."
