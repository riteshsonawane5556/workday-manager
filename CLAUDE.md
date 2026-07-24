# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Workday Manager** is a Personal Chief of Staff Agent — a FastAPI-based service that orchestrates pydantic-ai agents via a pydantic-graph state machine to triage email and manage calendar events using the Nylas API. Currently in Phase 2.

## Package Management

This project uses `uv` (not pip or poetry):

```bash
uv sync                              # install dependencies
uv add <package>                     # add a dependency
uv run alembic upgrade head          # apply DB migrations (run before first start)
uv run uvicorn main:app --reload     # dev server on http://localhost:8000
```

## Environment Variables

Copy `.env.example` and fill in:
- `NYLAS_API_KEY` + `NYLAS_GRANT_ID` — Nylas email/calendar credentials
- `GROQ_API_KEY` — LLM access (llama-3.3-70b-versatile)
- `USER_TIMEZONE` — IANA timezone string (default: `Asia/Kolkata`)
- `DATABASE_URL` — SQLAlchemy async DB URL (default: `sqlite+aiosqlite:///./workday.db`)

## Database & Migrations

SQLite (via SQLAlchemy 2.0 async + `aiosqlite`) backs the session and pending stores. Schema is owned by Alembic — run `uv run alembic upgrade head` before first start. To change the schema, edit the ORM models in `models/db_models.py`, then `uv run alembic revision --autogenerate -m "..."` and `uv run alembic upgrade head`. Alembic's `env.py` reads `DATABASE_URL` and runs migrations against the sync form of the URL (it strips `+aiosqlite`); the app uses the async form at runtime — both hit the same file.

## Pydantic AI

Read pydantic-ai docs at https://pydantic.dev/docs/ai/llms.txt before building or integrating anything AI-related.

## Observability

`logfire` is configured in `main.py` (service: `workday-manager`). It instruments both FastAPI and pydantic-ai with `include_content=True`. The custom `config/logger.py` layer also writes all agent run messages to `server.log` at DEBUG level via `log_agent_run`.

## Architecture

### Request Flow

```
POST /orchestrate  { "message": "...", "session_id": "..." (optional) }
  → session_id resolved (UUID generated if omitted)
  → per-session asyncio.Lock acquired (same session serialized; different sessions parallel)
  → session history + recent_events loaded from SessionStore
  → manager_agent.run(query, deps=WorkdayDeps, message_history=..., usage_limits=20 requests)
      calls tools as needed → returns ManagerOutput
  → save updated histories + recent_events back to SessionStore
  → return OrchestratorResult

POST /pending/{id}/approve
  → send_approved_email(item) → Nylas send + mark read → remove from pending_store
```

### Agents

| Agent | File | Model | Role | Output type |
|-------|------|-------|------|-------------|
| `manager_agent` | `agents/manager_agent.py` | llama-3.3-70b-versatile | Top-level orchestrator — routes via tools | `ManagerOutput` |
| `calendar_action_agent` | `agents/calendar_action_agent.py` | `groq:openai/gpt-oss-120b` | Calendar specialist — reads, books, reschedules, cancels, conflict checks | `str` |
| `email_node_agent` | `agents/email_node.py` | llama-3.3-70b-versatile | Classifies email + drafts reply | `EmailNodeOutput` |
| `compose_agent` | `agents/compose_agent.py` | llama-3.3-70b-versatile | Drafts new outbound emails | `DraftReply` |
| `synthesize_agent` | `agents/synthesize_agent.py` | llama-3.3-70b-versatile | Standalone briefing (not in main flow) | `str` |
| `planner_agent` | `agents/planner_agent.py` | llama-3.3-70b-versatile | Phase 1/2 remnant — not in main flow | `AgentDecision` |
| `email_agent` | `agents/email_agent.py` | llama-3.3-70b-versatile | Phase 1 remnant — not in main flow | `str` |
| `send_agent` | `agents/send_agent.py` | llama-3.3-70b-versatile | Phase 1 remnant — not in main flow | `str` |

`calendar_action_agent` uses `gpt-oss-120b` because it requires reliable multi-step tool reasoning for stop-and-confirm workflows.

### manager_agent Tool Dispatch

`manager_agent` is the single entry point — it picks tools based on intent:

```
manage_calendar   → delegates to calendar_action_agent (all calendar ops)
triage_inbox      → calls services/inbox_service.py run_inbox_triage()
compose_email     → stages outbound DraftReply via stage_outbound_draft()
send_meeting_invitation → add_participant() on Nylas + compose_agent + stage_outbound_draft()
(conversational)  → responds directly without any tool call
```

`manager_agent` carries `WorkdayDeps` which includes a `WorkdayMemory` sink. `calendar_action_agent` writes created/updated events to `WorkdayMemory.recent_events` via `CalendarDeps.sink`. This lets `send_meeting_invitation` reference the event from the same turn without extra DB roundtrips.

**Sequencing constraint:** `send_meeting_invitation` must be called AFTER `manage_calendar` when creating a meeting AND inviting someone. The agent's system prompt enforces this.

### Session & State Storage

SQLite-backed (SQLAlchemy 2.0 async), persists across restarts. ORM tables in `models/db_models.py`.

```
graph/session_store.py (SessionStore)      graph/pending_store.py (PendingStore)
        ↓ delegates to                              ↓ delegates to
services/session_service.py                services/pending_service.py
        ↓ calls                                     ↓ calls
repository/session_repository.py           repository/pending_repository.py
        ↓                                           ↓
repository/session_event_repository.py     config/database.py get_session()
```

- `SessionStore` — stores manager + calendar_action message histories plus `recent_events` (via `session_event_repository`). Fetched with cap of `_FETCH_LIMIT = 20` most-recent per agent type. `session_name` auto-derived from first 80 chars of user prompt.
- `PendingStore` — actionable emails awaiting approval, keyed by UUID (`pending_item` table). `send_approved_email` in `services/pending_service.py`.
- `session_event_repository` — upserts/fetches `SessionEventRow` rows (calendar events seen this session), enabling cross-turn event reference.

**Concurrency:** Per-session `asyncio.Lock` in `utils/graph_utils.py` (`get_session_lock`). Single-process only.

`utils/graph_utils.py` also owns `clean_email_body` (strips HTML, truncates to 2000 chars).

### inbox_service

`services/inbox_service.py` owns all email triage logic (previously spread across graph nodes):
- `run_inbox_triage(limit)` — fetches emails, skips already-pending/sent, classifies + drafts via `email_node_agent`, stores actionable drafts in `pending_store`, returns `(summary_str, pending_ids)`.
- `stage_outbound_draft(to, subject, body)` — wraps a user-composed email as an `EmailNodeOutput` and adds to `pending_store`.

### Key Models

**`models/orchestrator_models.py`**
- `WorkdayMemory` — in-memory sink for the current pipeline turn: `recent_events`, `email_pending_ids`, `calendar_changed`
- `WorkdayDeps` — agent deps: `user_tz`, `now_unix`, `now_label`, `working_memory`, `calendar_history`
- `RecentEvent` — lightweight event record stored in `WorkdayMemory` and persisted to `session_event`
- `ManagerOutput` — manager_agent output: `summary`, optional `clarification_question`
- `OrchestratorRequest` / `OrchestratorResult` — API request/response

**`models/email_models.py`**
- `EmailNodeOutput` — per-email triage result (classification + optional draft)
- `EmailClassification` — `urgent | fyi | actionable` + reasoning
- `DraftReply` — `subject`, `body`, `to`
- `PendingItem` — stored approval request (UUID id, email metadata, draft)
- `ProcessingResult` — pipeline summary (processed count, actionable count, pending_ids)

**`models/calendar_models.py`**
- `CalendarEvent` — id, title, start/end Unix timestamps, participants
- `CalendarDeps` — calendar agent deps: `user_tz`, `now_unix`, `now_label`, `sink` (WorkdayMemory)
- `CalendarActionResult` — description, executed, awaiting_user

### Nylas Integration (`config/nylas_client.py`, `tools/`)

Nylas SDK is synchronous; all calls wrapped in `asyncio.to_thread()`. Calendar tools use the first calendar on the account and filter by today's UTC date range. `clock_to_unix` in `tools/calendar_tools.py` converts wall-clock times to Unix via `USER_TIMEZONE`. `add_participant` in `tools/calendar_tools.py` patches an existing event to add an attendee.

### Routes

- `GET /health` — Verifies Nylas connection
- `POST /orchestrate` — Main entry point; accepts `OrchestratorRequest`, returns `OrchestratorResult`
- `GET /sessions` — List all sessions (id, name, timestamps)
- `GET /sessions/{session_id}/history` — Paginated manager message history as `turns`
- `GET /pending` — List pending approvals
- `POST /pending/{id}/approve` — Send the drafted reply
- `POST /pending/{id}/reject` — Discard without sending
- `GET /auth/status` — Stub (Phase 1, not implemented)

## Notes

- Do not add comments
- `controllers/` directory is reserved and currently empty
- `planner_agent`, `email_agent`, `send_agent`, `synthesize_agent` are Phase 1/2 remnants not connected to the main flow; do not remove until Phase 3 direction is clear
- CORS allows `http://localhost:5173` (Vite dev server for frontend)
