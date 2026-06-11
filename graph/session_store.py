from services.session_service import SessionHistory, get_session_history, save_session_history, clear_session


class SessionStore:
    async def get(self, session_id: str) -> SessionHistory:
        return await get_session_history(session_id)

    async def set(self, session_id: str, history: SessionHistory) -> None:
        await save_session_history(session_id, history)

    async def clear(self, session_id: str) -> None:
        await clear_session(session_id)


session_store = SessionStore()
