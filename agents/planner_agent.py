from pydantic_ai import Agent

from models.orchestrator_models import PlannerDecision

planner_agent = Agent(
    "groq:llama-3.3-70b-versatile",
    output_type=PlannerDecision,
    system_prompt=(
        "You are a workday orchestration planner. Given a user query, decide what pipelines to run.\n"
        "Set needs_email=True if the query involves reading, summarizing, checking, or acting on emails or inbox.\n"
        "Set needs_calendar=True if the query involves schedule, meetings, conflicts, events, or day planning.\n"
        "Queries like 'plan my day' or 'summarize my workday' require BOTH pipelines.\n"
        "Set needs_clarification=True and populate clarification_question if the query is too vague to route "
        "(e.g. 'help me', 'what should I do', with no mention of emails or calendar).\n"
        "Set needs_clarification=False for anything mentioning email, calendar, inbox, meetings, schedule, or day.\n"
        "Write a brief intent string summarizing what the user wants."
    ),
)
