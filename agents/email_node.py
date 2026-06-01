from pydantic_ai import Agent
from models.email_models import EmailNodeOutput
from tools.email_tools import fetch_email_body

email_node_agent = Agent(
    "groq:llama-3.3-70b-versatile",
    output_type=EmailNodeOutput,
    system_prompt=(
        "You are an email triage assistant. Given an email:\n"
        "1. Classify it as urgent, fyi, or actionable.\n"
        "   - urgent: requires immediate attention today\n"
        "   - actionable: needs a reply, not time-critical\n"
        "   - fyi: informational, no reply needed\n"
        "2. If actionable, draft a professional reply.\n"
        "Populate email_id, subject, sender exactly as given in the input.\n"
        "Set draft.to to the exact sender email address from the input — never guess or invent an address."
    ),
)


@email_node_agent.tool_plain
async def get_email_body(email_id: str) -> str:
    return await fetch_email_body(email_id)
