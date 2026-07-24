from services.session_service import (
    UnifiedHistory,
    get_unified,
    save_unified,
    clear_session,
)
from models.orchestrator_models import RecentEvent
from pydantic_ai.messages import ModelMessage


class SessionStore:
    async def get_unified(self, session_id: str) -> UnifiedHistory:
        return await get_unified(session_id)

    async def save_unified(
        self,
        session_id: str,
        manager_msgs: list[ModelMessage],
        calendar_msgs: list[ModelMessage],
        recent_events: list[RecentEvent],
        calendar_action_open: bool = False,
    ) -> None:
        await save_unified(session_id, manager_msgs, calendar_msgs, recent_events, calendar_action_open)

    async def clear(self, session_id: str) -> None:
        await clear_session(session_id)


session_store = SessionStore()
SessionHistory = UnifiedHistory
