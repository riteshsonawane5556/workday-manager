import json

from fastapi import APIRouter, HTTPException
from pydantic_ai.messages import ModelRequest, ModelResponse

from repository.session_repository import get_session_row, list_sessions
from services.session_service import get_unified

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("")
async def get_sessions():
    rows = await list_sessions()
    return [
        {
            "session_id": r.session_id,
            "session_name": r.session_name,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


@router.get("/{session_id}/history")
async def get_session_history_route(session_id: str):
    row = await get_session_row(session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    history = await get_unified(session_id)

    def extract_user_text(req: ModelRequest) -> str | None:
        for part in req.parts:
            if part.part_kind == "user-prompt":
                content = getattr(part, "content", "") or ""
                return content[:500] if content else None
        return None

    def extract_assistant_text(resp: ModelResponse) -> str | None:
        for part in resp.parts:
            if part.part_kind == "text":
                content = getattr(part, "content", "") or ""
                if content:
                    return content
            if part.part_kind == "tool-call" and getattr(part, "tool_name", None) == "final_result":
                try:
                    parsed = json.loads(part.args)
                    return parsed.get("summary") or parsed.get("clarification_question") or None
                except Exception:
                    return None
        return None

    turns = []
    msgs = history.manager
    i = 0
    while i < len(msgs):
        msg = msgs[i]
        user_text = extract_user_text(msg) if isinstance(msg, ModelRequest) else None
        if user_text is None:
            i += 1
            continue

        asst_text = None
        j = i + 1
        while j < len(msgs):
            nxt = msgs[j]
            if isinstance(nxt, ModelRequest) and extract_user_text(nxt) is not None:
                break
            if isinstance(nxt, ModelResponse):
                candidate = extract_assistant_text(nxt)
                if candidate:
                    asst_text = candidate
            j += 1

        if asst_text:
            turns.append({"role_user": user_text, "role_assistant": asst_text})
        i = j

    return {"session_id": session_id, "turns": turns}
