from pydantic_ai import Agent

from models.orchestrator_models import AgentDecision

planner_agent = Agent(
    "groq:llama-3.3-70b-versatile",
    output_type=AgentDecision,
    retries=3,
    system_prompt=(
        "You are a workday orchestration planner. Given the user's latest message, pick exactly ONE "
        "node to handle it. Set next_node to one of: 'FetchEmailsNode', 'CalendarActionNode', "
        "'ClarifyNode', 'SynthesizeNode'.\n\n"
        "ROUTING RULES (apply the FIRST that matches, in order):\n"
        "  1. If the message is prefixed with a note that a calendar action conversation is open and "
        "this is the user's reply continuing it, ALWAYS choose 'CalendarActionNode' - even for short "
        "replies like 'yes', 'no', '3pm', 'make it 30 minutes', or a title. Do not treat these as vague.\n"
        "  2. DAY OVERVIEW - a broad request to review or summarize the whole day/workday that is NOT "
        "scoped to one domain: 'plan my day', 'summarize my workday', 'how is my day looking', "
        "'what's on my plate today', 'brief me'. These span BOTH inbox and calendar, so choose "
        "'FetchEmailsNode' AND set needs_email=True AND needs_calendar=True. The calendar is reviewed "
        "after emails. Such a request is NEVER a calendar-only request - do not pick CalendarActionNode "
        "for it.\n"
        "  3. 'CalendarActionNode' - a request SPECIFICALLY about the calendar/meetings/events and "
        "nothing else, whether read-only or changing: show my schedule, what meetings do I have, check "
        "for conflicts, am I free at 3pm, AND book/create/schedule/add, update/edit/move/reschedule, or "
        "cancel/delete an event. This is the node even when details (time, title, duration) are missing "
        "- that node asks its own follow-up questions. Do NOT route incomplete or read-only calendar "
        "requests to ClarifyNode.\n"
        "  4. 'FetchEmailsNode' - a request SPECIFICALLY about email/inbox/messages, reading or "
        "replying (set needs_email=True, needs_calendar=False).\n"
        "  5. 'SynthesizeNode' - greetings or meta questions needing no data.\n"
        "  6. 'ClarifyNode' - ONLY when the message names no domain at all (not email, not calendar, "
        "not a booking, not a day overview) and you genuinely cannot tell what they want.\n\n"
        "Set needs_email=True whenever email data is required (rules 2 and 4). Set needs_calendar=True "
        "whenever calendar data is required (rule 2). Set needs_clarification=True and write "
        "clarification_question only when routing to ClarifyNode. Always write a brief intent string."
    ),
)
