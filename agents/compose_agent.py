from pydantic_ai import Agent

from models.email_models import DraftReply

compose_agent = Agent(
    "groq:llama-3.3-70b-versatile",
    output_type=DraftReply,
    retries=3,
    system_prompt=(
        "You compose a brand-new outbound email from the user's instruction. Produce a DraftReply "
        "with three fields: to (the recipient's email address), subject (concise), and body (a "
        "complete, professional message written in the user's voice).\n\n"
        "RULES:\n"
        "  - 'to' MUST be a real email address copied verbatim from the user's instruction. Never "
        "invent, guess, or complete a partial address.\n"
        "  - If the instruction names a person but gives NO email address (e.g. just 'Sarah'), set "
        "to='' and still write the subject and body - the caller will ask the user for the address.\n"
        "  - Write a sensible subject if the user did not give one.\n"
        "  - Keep the body short, natural, and ready to send."
    ),
)
