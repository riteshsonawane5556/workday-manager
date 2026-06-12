import re

from fastapi import APIRouter, HTTPException
from pydantic_ai.messages import ModelRequest, ModelResponse

from repository.session_repository import get_session_row, list_sessions
from services.session_service import get_session_history

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

    history = await get_session_history(session_id)

    turns = []
    reqs = [m for m in history.synthesize if isinstance(m, ModelRequest)]
    resps = [m for m in history.synthesize if isinstance(m, ModelResponse)]

    for req, resp in zip(reqs, resps):
        user_text = None
        for part in req.parts:
            if part.part_kind == "user-prompt":
                content = getattr(part, "content", "") or ""
                match = re.search(
                    r'(?:conversational message|User query):\s*"([^"]+)"', content
                )
                if match:
                    user_text = match.group(1)
                break

        asst_text = None
        for part in resp.parts:
            if part.part_kind == "text":
                asst_text = getattr(part, "content", "") or ""
                break

        if user_text and asst_text:
            turns.append({"role_user": user_text, "role_assistant": asst_text})

    return {"session_id": session_id, "turns": turns}
