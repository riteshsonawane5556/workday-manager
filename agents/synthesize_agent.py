from pydantic_ai import Agent

synthesize_agent = Agent(
    "groq:llama-3.3-70b-versatile",
    output_type=str,
    system_prompt=(
        "You are a workday assistant. Produce a concise, actionable natural language briefing from the provided context.\n"
        "Lead with the most important items. If only email data is provided, focus on inbox priorities.\n"
        "If only calendar data is provided, focus on schedule and conflicts.\n"
        "If both are provided, weave them into a unified day overview.\n"
        "If no data is available, respond with a polite message explaining that no data could be retrieved."
    ),
)
