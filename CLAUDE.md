# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Workday Manager** is a Personal Chief of Staff Agent — a FastAPI-based service that orchestrates pydantic-ai agents via a pydantic-graph state machine to triage email and analyze calendar conflicts using the Nylas API. Currently in Phase 2.

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
POST /orchestrate  { "query": "..." }
  → OrchestratorState initialized
  → PlannerNode (planner_agent decides intent)
    → FetchEmailsNode → ClassifyNode × N → DraftNode → HumanGateNode → BuildEmailResultNode
    → FetchCalendarNode → CalendarNode
    → ClarifyNode (ambiguous query)
  → SynthesizeNode → returns OrchestratorResult

POST /pending/{id}/approve
  → send_approved_email(item) → Nylas send + mark read
  → remove from pending_store
```

### Agents

All agents use `groq:llama-3.3-70b-versatile` via pydantic-ai.

| Agent | File | Role | Output type |
|-------|------|------|-------------|
| `planner_agent` | `agents/planner_agent.py` | Routes query to correct pipeline node | `AgentDecision` |
| `email_node_agent` | `agents/email_node.py` | Classifies email + drafts reply (tool: `get_email_body`) | `EmailNodeOutput` |
| `send_agent` | `agents/send_agent.py` | Sends approved drafts (tool: `send_email`) | `str` |
| `calendar_agent` | `agents/calendar_agent.py` | Analyzes calendar conflicts, suggests reschedules | `CalendarAnalysisResult` |
| `synthesize_agent` | `agents/synthesize_agent.py` | Produces final natural-language briefing | `str` |
| `email_agent` | `agents/email_agent.py` | Generic email assistant (tool: `list_emails`) | `str` |

### Pydantic-Graph State Machine

Single unified pipeline in `graph/planner_graph.py` — State: `OrchestratorState` (query, decision, emails, email_outputs, pending_ids, calendar events/conflicts, results).

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
  │                              ├─(needs_calendar)→ FetchCalendarNode → CalendarNode
  │                              └─────────────────────────────────────→ SynthesizeNode
  ├─(needs_calendar only)→ FetchCalendarNode → CalendarNode → SynthesizeNode
  └─(unclear)→ ClarifyNode (returns clarification_question, no pipeline run)
```

### Human-in-the-Loop

Actionable emails with drafted replies are stored in `graph/pending_store.py` (in-memory dict, keyed by UUID). The `/pending` routes expose list / approve / reject.

### Key Models

**`models/orchestrator_models.py`**
- `AgentDecision` — planner output: intent, next_node, needs_email, needs_calendar, clarification
- `OrchestratorState` — full pipeline state (dataclass)
- `OrchestratorResult` — API response: summary, email_result, calendar_result, clarification_question

**`models/email_models.py`**
- `EmailMeta` — id, subject, sender, date, snippet, is_unread
- `EmailNodeOutput` — per-email triage (classification + optional draft)
- `EmailClassification` — `urgent | fyi | actionable` + reasoning
- `DraftReply` — subject, body, to
- `PendingItem` — stored approval request (UUID id, email metadata, draft)
- `ProcessingResult` — pipeline summary (processed count, actionable count, pending_ids)

**`models/calendar_models.py`**
- `CalendarEvent` — id, title, start_time/end_time (Unix), participants
- `ConflictPair` — two overlapping events
- `RescheduleSuggestion` — event_id, suggested_start, reasoning
- `CalendarAnalysisResult` — date, total_events, conflicts, suggestions, summary

### Services and Utils

- `services/pending_service.py` — `send_approved_email(item)`: sends via Nylas, marks original email read
- `services/calendar_service.py` — `fetch_calendar_data()` and `detect_conflicts()` (O(n²) overlap check)
- `utils/calendar_utils.py` — `build_calendar_prompt()`: formats events + conflicts into LLM-readable text

### Nylas Integration (`config/nylas_client.py`, `tools/`)

Nylas SDK is synchronous; all calls are wrapped in `asyncio.to_thread()`. HTML is stripped and bodies truncated to 2000 chars before passing to the LLM. Calendar tools use the first calendar on the account and filter by today's UTC date range.

### Routes

- `GET /health` — Verifies Nylas connection
- `POST /orchestrate` — Main entry point; accepts `{ "query": "..." }`, returns `OrchestratorResult`
- `POST /calendar/analyze` — Standalone calendar conflict analysis
- `GET /auth/status` — Stub (Phase 1, not implemented)
- `GET /pending` — List pending approvals
- `POST /pending/{id}/approve` — Send the drafted reply
- `POST /pending/{id}/reject` — Discard without sending

## Notes

- Do not add comments
- `controllers/` and `repository/` directories are reserved and currently empty
- `pending_store` is in-memory only — restarts clear all pending items
