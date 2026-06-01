# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Workday Manager** is a Personal Chief of Staff Agent — a FastAPI-based service that orchestrates pydantic-ai agents via a pydantic-graph state machine to triage and respond to email using the Nylas API. Currently in Phase 2.

## Package Management

This project uses `uv` (not pip or poetry):

```bash
uv sync                              # install dependencies
uv add <package>                     # add a dependency
uv run uvicorn main:app --reload     # dev server on http://localhost:8000
```

## Environment Variables

Copy `.env.example` and fill in:
- `NYLAS_API_KEY` + `NYLAS_GRANT_ID` — Nylas email credentials
- `GROQ_API_KEY` — LLM access (llama-3.3-70b-versatile)

## Pydantic AI

Read pydantic-ai docs at https://pydantic.dev/docs/ai/llms.txt before building or integrating anything AI-related.

## Architecture

### Request Flow

```
POST /chat
  → run_email_pipeline()
    → FetchEmailsNode (Nylas API)
    → ClassifyNode × N (email_node_agent per email)
    → DraftNode → HumanGateNode (if actionable)
  → returns ProcessingResult

POST /pending/{id}/approve
  → send_agent sends email via Nylas
  → removes item from pending_store
```

### Three-Agent System

All agents use `groq:llama-3.3-70b-versatile` via pydantic-ai.

| Agent | File | Role | Output type |
|-------|------|------|-------------|
| `email_agent` | `agents/email_agent.py` | Lists unread emails (tool: `get_unread_emails`) | `str` |
| `email_node_agent` | `agents/email_node.py` | Classifies email + drafts reply (tool: `get_email_body`) | `EmailNodeOutput` |
| `send_agent` | `agents/send_agent.py` | Sends approved drafts (tool: `send_email`, `requires_approval=True`) | `str` |

### Pydantic-Graph State Machine (`graph/email_graph.py`)

State: `EmailPipelineState` holds fetched emails, `current_index`, outputs list, and `pending_ids`.

Nodes: `FetchEmailsNode → ClassifyNode → DraftNode → HumanGateNode → ClassifyNode` (loops until all emails processed, then ends with `ProcessingResult`).

### Human-in-the-Loop

Actionable emails are stored in `graph/pending_store.py` (in-memory dict, keyed by UUID). The `/pending` routes expose list / approve / reject. Approval calls `send_agent` with pydantic-ai's `DeferredToolRequests/Results` pattern.

### Key Models (`models/email_models.py`)

- `EmailMeta` — id, subject, sender, date, snippet, is_unread
- `EmailNodeOutput` — per-email triage result (classification + optional draft)
- `EmailClassification` — `urgent | fyi | actionable` + reasoning
- `DraftReply` — subject, body, to
- `PendingItem` — stored approval request (UUID id, email metadata, draft)
- `ProcessingResult` — final pipeline summary

### Nylas Integration (`config/nylas_client.py`, `tools/email_tools.py`)

Nylas SDK is synchronous; all calls are wrapped in `asyncio.to_thread()`. HTML is stripped and bodies truncated to 2000 chars before passing to the LLM.

### Routes

- `GET /health` — Verifies Nylas connection
- `POST /chat` — Triggers the full email pipeline
- `GET /auth/status` — Stub (Phase 1, not implemented)
- `GET /pending` — List pending approvals
- `POST /pending/{id}/approve` — Send the drafted reply
- `POST /pending/{id}/reject` — Discard without sending

## Notes

- Do not add comments
- `controllers/`, `repository/`, `utils/` directories are reserved and currently empty
- `pending_store` is in-memory only — restarts clear all pending items
