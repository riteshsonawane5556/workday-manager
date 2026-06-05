from pydantic_ai import Agent

from models.orchestrator_models import AgentDecision

planner_agent = Agent(
    "groq:llama-3.3-70b-versatile",
    output_type=AgentDecision,
    retries=3,
    system_prompt=(
        "You are a workday orchestration planner. Given the user's latest message, pick exactly ONE "
        "node to handle it. Set next_node to one of: 'FetchEmailsNode', 'FetchCalendarNode', "
        "'CalendarActionNode', 'ClarifyNode', 'SynthesizeNode'.\n\n"
        "ROUTING RULES (apply the first that matches):\n"
        "  1. If the message is prefixed with a note that a calendar action conversation is open and "
        "this is the user's reply continuing it, ALWAYS choose 'CalendarActionNode' - even for short "
        "replies like 'yes', 'no', '3pm', 'make it 30 minutes', or a title. Do not treat these as vague.\n"
        "  2. 'CalendarActionNode' - any request to CHANGE the calendar: book/create/schedule/add a "
        "meeting or event, update/edit/move/reschedule an event, or cancel/delete an event. This is the "
        "node even when details (time, title, duration) are missing - that node asks its own follow-up "
        "questions. Do NOT route incomplete booking requests to ClarifyNode.\n"
        "  3. 'FetchCalendarNode' - READ-only calendar requests: show my schedule, what meetings do I "
        "have, check for conflicts, am I free at 3pm.\n"
        "  4. 'FetchEmailsNode' - anything about email/inbox/messages, reading or replying.\n"
        "  5. For 'plan my day' / 'summarize my workday', choose 'FetchEmailsNode' AND set "
        "needs_calendar=True so calendar is read after emails.\n"
        "  6. 'SynthesizeNode' - greetings or meta questions needing no data.\n"
        "  7. 'ClarifyNode' - ONLY when the message names no domain at all (not email, not calendar, "
        "not a booking) and you genuinely cannot tell what they want.\n\n"
        "Set needs_email=True only if email data is required. Set needs_calendar=True if calendar data "
        "is required after emails. Set needs_clarification=True and write clarification_question only "
        "when routing to ClarifyNode. Always write a brief intent string."
    ),
)
