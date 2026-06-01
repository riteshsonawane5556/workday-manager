from pydantic_ai import Agent
from models.email_models import AgentResponse, EmailMeta
from tools.email_tools import list_emails

email_agent = Agent(
    "anthropic:claude-sonnet-4-6",
    result_type=AgentResponse,
    system_prompt=(
        "You are a workday manager. Help the user manage their inbox efficiently. "
        "Be concise and action-oriented. When asked about emails, use the list_emails "
        "tool to fetch them and summarize what needs attention."
    ),
)


@email_agent.tool_plain
async def get_unread_emails(n: int = 10) -> list[EmailMeta]:
    """Fetch the n most recent unread emails from the connected inbox."""
    return await list_emails(n)
