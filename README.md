You are an expert Python backend engineer. Help me build Phase 1 of a Personal Chief of Staff Agent.

## Goal
Set up the project foundations: repo structure, FastAPI skeleton, a pydantic-ai Agent,
and one working tool — `list_emails` via Nylas Python SDK v3. Everything must be
end-to-end testable before any complexity is added.

## Tech Stack (Phase 1 only)
- Python 3.12+, uv for package management
- FastAPI with async support
- pydantic-ai for the agent
- Nylas Python SDK v3 (pip install nylas) for email access
- .env via python-dotenv

## Nylas Setup (important context)
Nylas v3 uses two credentials:
- NYLAS_API_KEY    — your server-side API key from the Nylas dashboard
- NYLAS_GRANT_ID  — the connected account identifier (email address or grant ID)
                    obtained after authenticating a user account via Nylas Hosted OAuth

The client is initialized as:
  from nylas import Client
  nylas = Client(api_key=NYLAS_API_KEY)

Then all calls pass the grant_id as the first argument:
  nylas.messages.list(NYLAS_GRANT_ID, query_params={...})

No token.json, no Google OAuth flow — Nylas handles all of that via their dashboard
or hosted auth flow. The NYLAS_GRANT_ID is stored in .env after one-time setup.

## What to build

### 1. Project bootstrap
- project is Initialized with uv already. create pyproject.toml with all dependencies:
  nylas, fastapi, uvicorn, pydantic-ai, pydantic, python-dotenv
- .env.example:
    NYLAS_API_KEY=
    NYLAS_GRANT_ID=
    ANTHROPIC_API_KEY=        # or OPENAI_API_KEY depending on your LLM choice
- .gitignore covering .env, __pycache__, .venv

### 2. Nylas client singleton
 — initializes and exports a single `nylas` Client instance
  loaded from environment variables. All tools import from here.

### 3. list_emails tool
- tools/email_tools.py — a single async function `list_emails(n: int = 10)`
- Uses nylas.messages.list() with query_params={"limit": n, "unread": True}
- Returns List[EmailMeta] where EmailMeta is a Pydantic model:
    id: str
    subject: str
    sender: str        # from nylas message.from_ field
    date: str          # human-readable
    snippet: str
    is_unread: bool

### 4. pydantic-ai Agent
- agents/email_agent.py — a pydantic-ai Agent with the list_emails tool registered
- System prompt: "You are a workday manager. Help the user manage their inbox
  efficiently. Be concise and action-oriented."
- Use structured output: return AgentResponse(summary: str, emails: List[EmailMeta])

### 5. FastAPI app
- main.py — FastAPI app with:
  - GET  /health        → { "status": "ok", "nylas": "connected" }
  - POST /chat          → accepts ChatRequest(message: str), runs the agent,
                          returns ChatResponse(reply: str)



## Constraints
- No database yet (Phase 5)
- No task queue yet (Phase 7)
- No Slack or Calendar tools yet (even though Nylas supports them)
- Do NOT send or draft emails in Phase 1 — read-only
- All tool functions must be async (use asyncio.to_thread() to wrap
  synchronous Nylas SDK calls since the Python SDK is sync)

## Folder Structure
- config : all configurations like db, ai, nylas etc.
- routes
    - auth
        auth_schema.py
        auth_route.py
- models
- controllers
- repository
- utils
- graph
