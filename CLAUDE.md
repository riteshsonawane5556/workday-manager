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

## Architecture

### Request Flow

```
POST /orchestrate  { "message": "...", "session_id": "..." }
  → OrchestratorState initialized (session history loaded from SessionStore)
  → PlannerNode (planner_agent decides intent)
    → FetchEmailsNode → ClassifyNode × N → DraftNode → HumanGateNode → BuildEmailResultNode
    → CalendarActionNode (agentic: reads, books, reschedules, cancels, flags conflicts)
    → ClarifyNode (ambiguous query)
  → SynthesizeNode → returns OrchestratorResult

POST /pending/{id}/approve
  → send_approved_email(item) → Nylas send + mark read
  → remove from pending_store
```

### Agents

| Agent | File | Model | Role | Output type |
|-------|------|-------|------|-------------|
| `planner_agent` | `agents/planner_agent.py` | llama-3.3-70b-versatile | Routes query to correct pipeline node | `AgentDecision` |
| `email_node_agent` | `agents/email_node.py` | llama-3.3-70b-versatile | Classifies email + drafts reply (tool: `get_email_body`) | `EmailNodeOutput` |
| `calendar_action_agent` | `agents/calendar_action_agent.py` | `groq:openai/gpt-oss-120b` | Agentic calendar assistant — reads, books, reschedules, cancels, and flags conflicts via tools (`get_events`, `check_conflicts`, `create_event`, `update_event`, `delete_event`) | `str` |
| `synthesize_agent` | `agents/synthesize_agent.py` | llama-3.3-70b-versatile | Produces final natural-language briefing | `str` |
| `email_agent` | `agents/email_agent.py` | llama-3.3-70b-versatile | Generic email assistant (tool: `get_unread_emails`) | `str` |
| `send_agent` | `agents/send_agent.py` | llama-3.3-70b-versatile | Sends approved drafts (tool: `send_email`) | `str` |

`calendar_action_agent` uses `gpt-oss-120b` (not the default llama) because it requires reliable multi-step tool reasoning for stop-and-confirm workflows.

### Pydantic-Graph State Machine

Single unified pipeline in `graph/planner_graph.py` — State: `OrchestratorState` (message, decision, emails, email_outputs, pending_ids, results, conversation histories).

**Node flow:**
```
PlannerNode
  ├─(needs_email)→ FetchEmailsNode → ClassifyNode ─(loop)─┐
  │                                     ↓(actionable+draft) │
  │                                   DraftNode             │
  │                                     ↓                   │
  │                                HumanGateNode ──────────┘
  │                                     ↓(all done)
  │                            BuildEmailResultNode
  │                              ├─(needs_calendar)→ CalendarActionNode → SynthesizeNode
  │                              └─────────────────────────────────────→ SynthesizeNode
  ├─(calendar request)→ CalendarActionNode → SynthesizeNode
  └─(unclear)→ ClarifyNode (returns clarification_question, no pipeline run)
```

`CalendarActionNode` runs the agentic `calendar_action_agent` for ALL calendar requests — read-only (show schedule, check conflicts, am I free) and changes (book/reschedule/cancel). The agent reasons over its own tool results; there is no separate conflict-detection node. Multi-turn confirmations are tracked via `calendar_action_open` in the `SessionStore`.

### Session & State Storage

Both stores are SQLite-backed (SQLAlchemy 2.0 async) and **persist across restarts**. Their async methods (`get`/`set`, `add`/`list_all`/`get`/`has_email`/`remove`) acquire a session via `config/database.py`'s `get_session()`. ORM tables live in `models/db_models.py`.

- `graph/session_store.py` (`SessionStore`) — per-session conversation histories (planner, calendar_action, synthesize) plus the `calendar_action_open` flag, keyed by `session_id`. Message lists are serialized to JSON columns via pydantic-ai's `ModelMessagesTypeAdapter` (`session_history` table).
- `graph/pending_store.py` (`PendingStore`) — actionable emails awaiting human approval, keyed by UUID, with the `DraftReply` stored as JSON (`pending_item` table).

### Key Models

**`models/orchestrator_models.py`**
- `AgentDecision` — planner output: intent, next_node, needs_email, needs_calendar, clarification_question
- `OrchestratorRequest` — API request: message, optional session_id
- `OrchestratorState` — full pipeline state (dataclass)
- `OrchestratorResult` — API response: summary, email_result, calendar_action_result, clarification_question

**`models/email_models.py`**
- `EmailMeta` — id, subject, sender, date, snippet, is_unread
- `EmailNodeOutput` — per-email triage (classification + optional draft)
- `EmailClassification` — `urgent | fyi | actionable` + reasoning
- `DraftReply` — subject, body, to
- `PendingItem` — stored approval request (UUID id, email metadata, draft)
- `ProcessingResult` — pipeline summary (processed count, actionable count, pending_ids)

**`models/calendar_models.py`**
- `CalendarEvent` — id, title, start_time/end_time (Unix timestamps), participants
- `ConflictPair` — two overlapping events (built inside the agent's `check_conflicts` tool)
- `CalendarDeps` — agent run deps: user_tz, now_unix, now_label, changed_calendar
- `CalendarActionResult` — description, executed, awaiting_user

### Nylas Integration (`config/nylas_client.py`, `tools/`)

Nylas SDK is synchronous; all calls are wrapped in `asyncio.to_thread()`. HTML is stripped and email bodies truncated to 2000 chars before passing to the LLM. Calendar tools use the first calendar on the account and filter by today's UTC date range. The `clock_to_unix` helper in `tools/calendar_tools.py` converts wall-clock times to Unix timestamps using `USER_TIMEZONE`.

### Routes

- `GET /health` — Verifies Nylas connection
- `POST /orchestrate` — Main entry point; accepts `OrchestratorRequest`, returns `OrchestratorResult`
- `GET /auth/status` — Stub (Phase 1, not implemented)
- `GET /pending` — List pending approvals
- `POST /pending/{id}/approve` — Send the drafted reply
- `POST /pending/{id}/reject` — Discard without sending

## Notes

- Do not add comments
- `controllers/` and `repository/` directories are reserved and currently empty
- Both in-memory stores (`pending_store`, `session_store`) are cleared on server restart
