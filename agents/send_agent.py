from pydantic_ai import Agent, RunContext
from config.nylas_client import nylas, NYLAS_GRANT_ID

send_agent = Agent(
    "groq:llama-3.3-70b-versatile",
    system_prompt="You are an email sending assistant. When asked to send an email, use the send_email tool.",
)


@send_agent.tool
def send_email(ctx: RunContext[None], subject: str, body: str, to: str) -> str:
    nylas.messages.send(
        NYLAS_GRANT_ID,
        {"subject": subject, "body": body, "to": [{"email": to}]},
    )
    return f"Email sent to {to}"
