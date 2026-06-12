from sqlalchemy import delete, exists, select, update

from config.database import get_session
from models.db_models import PendingItemRow


async def insert_pending_item(
    item_id: str,
    email_id: str,
    subject: str,
    sender: str,
    draft_json: str,
) -> None:
    async with get_session() as db:
        db.add(PendingItemRow(
            id=item_id,
            email_id=email_id,
            subject=subject,
            sender=sender,
            draft=draft_json,
        ))
        await db.commit()


async def list_pending_items() -> list[PendingItemRow]:
    async with get_session() as db:
        rows = (await db.execute(select(PendingItemRow))).scalars().all()
        return list(rows)


async def get_pending_item(item_id: str) -> PendingItemRow | None:
    async with get_session() as db:
        return await db.get(PendingItemRow, item_id)


async def pending_email_exists(email_id: str) -> bool:
    async with get_session() as db:
        result = await db.execute(
            select(exists().where(PendingItemRow.email_id == email_id))
        )
        return bool(result.scalar())


async def update_pending_draft(item_id: str, draft_json: str) -> int:
    async with get_session() as db:
        result = await db.execute(
            update(PendingItemRow)
            .where(PendingItemRow.id == item_id)
            .values(draft=draft_json)
        )
        await db.commit()
        return result.rowcount


async def delete_pending_item(item_id: str) -> int:
    async with get_session() as db:
        result = await db.execute(
            delete(PendingItemRow).where(PendingItemRow.id == item_id)
        )
        await db.commit()
        return result.rowcount
