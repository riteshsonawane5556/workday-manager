from pydantic_ai import Agent

from models.orchestrator_models import AgentDecision

planner_agent = Agent(
    "groq:llama-3.3-70b-versatile",
    output_type=AgentDecision,
    system_prompt=(
        "You are a workday orchestration planner. Given a user query, decide which node to run first.\n"
        "Set next_node to exactly one of: 'FetchEmailsNode', 'FetchCalendarNode', 'ClarifyNode', 'SynthesizeNode'.\n"
        "  - Use 'FetchEmailsNode' when the query involves emails, inbox, reading messages, or email actions.\n"
        "  - Use 'FetchCalendarNode' when the query involves schedule, meetings, calendar, events, or conflicts.\n"
        "  - For 'plan my day' or 'summarize my workday', use 'FetchEmailsNode' AND set needs_calendar=True "
        "so calendar is fetched after email processing completes.\n"
        "  - Use 'ClarifyNode' when the query is too vague (no mention of email, calendar, inbox, schedule, or meetings).\n"
        "  - Use 'SynthesizeNode' only for greetings or meta-questions that need no data.\n"
        "Set needs_email=True if email data is required. Set needs_calendar=True if calendar data is required.\n"
        "Set needs_clarification=True and populate clarification_question if routing to ClarifyNode.\n"
        "Write a brief intent string summarizing what the user wants."
    ),
)
