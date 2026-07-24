import json

from sqlalchemy import delete, select

from config.database import get_session
from models.db_models import SessionEventRow


async def upsert_session_events(session_id: str, events: list[dict]) -> None:
    async with get_session() as db:
        await db.execute(
            delete(SessionEventRow).where(SessionEventRow.session_id == session_id)
        )
        for e in events:
            db.add(SessionEventRow(
                session_id=session_id,
                event_id=e["id"],
                title=e["title"],
                start_unix=e["start_unix"],
                end_unix=e["end_unix"],
                attendees=json.dumps(e.get("attendees", [])),
            ))
        await db.commit()


async def fetch_session_events(session_id: str) -> list[dict]:
    async with get_session() as db:
        stmt = select(SessionEventRow).where(SessionEventRow.session_id == session_id)
        rows = (await db.execute(stmt)).scalars().all()
        return [
            {
                "id": row.event_id,
                "title": row.title,
                "start_unix": row.start_unix,
                "end_unix": row.end_unix,
                "attendees": json.loads(row.attendees),
            }
            for row in rows
        ]
