from sqlalchemy import delete, select

from config.database import get_session
from models.db_models import SessionMessageRow, SessionRow

_FETCH_LIMIT = 20


async def get_session_row(session_id: str) -> SessionRow | None:
    async with get_session() as db:
        return await db.get(SessionRow, session_id)


async def fetch_agent_messages(session_id: str, agent_type: str) -> list[SessionMessageRow]:
    async with get_session() as db:
        stmt = (
            select(SessionMessageRow)
            .where(
                SessionMessageRow.session_id == session_id,
                SessionMessageRow.agent_type == agent_type,
            )
            .order_by(SessionMessageRow.sequence.desc())
            .limit(_FETCH_LIMIT)
        )
        rows = (await db.execute(stmt)).scalars().all()
        return list(reversed(rows))


async def upsert_session(
    session_id: str,
    calendar_action_open: bool,
    session_name: str | None,
    messages_by_agent: dict[str, list[tuple[int, str, str]]],
) -> None:
    async with get_session() as db:
        session_row = await db.get(SessionRow, session_id)
        if session_row is None:
            session_row = SessionRow(session_id=session_id)
            db.add(session_row)
        session_row.calendar_action_open = calendar_action_open
        if session_row.session_name is None and session_name is not None:
            session_row.session_name = session_name

        for agent_type, entries in messages_by_agent.items():
            await db.execute(
                delete(SessionMessageRow).where(
                    SessionMessageRow.session_id == session_id,
                    SessionMessageRow.agent_type == agent_type,
                )
            )
            for seq, role, message_json in entries:
                db.add(SessionMessageRow(
                    session_id=session_id,
                    agent_type=agent_type,
                    role=role,
                    sequence=seq,
                    message_json=message_json,
                ))
        await db.commit()


async def delete_session(session_id: str) -> None:
    async with get_session() as db:
        await db.execute(
            delete(SessionMessageRow).where(SessionMessageRow.session_id == session_id)
        )
        await db.execute(
            delete(SessionRow).where(SessionRow.session_id == session_id)
        )
        await db.commit()
