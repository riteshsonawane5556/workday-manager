from pydantic_ai import Agent

synthesize_agent = Agent(
    "groq:llama-3.3-70b-versatile",
    output_type=str,
    instructions="Retired — replaced by manager_agent.",
)
