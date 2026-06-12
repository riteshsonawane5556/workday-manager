from sqlalchemy import exists, select

from config.database import get_session
from models.db_models import SentEmailRow


async def insert_sent_email(email_id: str) -> None:
    async with get_session() as db:
        existing = await db.get(SentEmailRow, email_id)
        if existing is None:
            db.add(SentEmailRow(email_id=email_id))
            await db.commit()


async def sent_email_exists(email_id: str) -> bool:
    async with get_session() as db:
        result = await db.execute(
            select(exists().where(SentEmailRow.email_id == email_id))
        )
        return bool(result.scalar())
