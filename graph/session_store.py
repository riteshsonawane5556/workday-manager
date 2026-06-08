from dataclasses import dataclass, field

from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from sqlalchemy import delete, select

from config.database import get_session
from models.db_models import SessionHistoryRow


@dataclass
class SessionHistory:
    planner: list[ModelMessage] = field(default_factory=list)
    calendar_action: list[ModelMessage] = field(default_factory=list)
    synthesize: list[ModelMessage] = field(default_factory=list)
    calendar_action_open: bool = False


def _load(raw: str | None) -> list[ModelMessage]:
    if not raw:
        return []
    return list(ModelMessagesTypeAdapter.validate_json(raw))


def _dump(messages: list[ModelMessage]) -> str:
    return ModelMessagesTypeAdapter.dump_json(messages).decode("utf-8")


class SessionStore:
    async def get(self, session_id: str) -> SessionHistory:
        async with get_session() as session:
            row = await session.get(SessionHistoryRow, session_id)
            if row is None:
                return SessionHistory()
            return SessionHistory(
                planner=_load(row.planner),
                calendar_action=_load(row.calendar_action),
                synthesize=_load(row.synthesize),
                calendar_action_open=row.calendar_action_open,
            )

    async def set(self, session_id: str, history: SessionHistory) -> None:
        async with get_session() as session:
            row = await session.get(SessionHistoryRow, session_id)
            if row is None:
                row = SessionHistoryRow(session_id=session_id)
                session.add(row)
            row.planner = _dump(history.planner)
            row.calendar_action = _dump(history.calendar_action)
            row.synthesize = _dump(history.synthesize)
            row.calendar_action_open = history.calendar_action_open
            await session.commit()

    async def clear(self, session_id: str) -> None:
        async with get_session() as session:
            await session.execute(
                delete(SessionHistoryRow).where(
                    SessionHistoryRow.session_id == session_id
                )
            )
            await session.commit()


session_store = SessionStore()
