import uuid

from sqlalchemy import delete, exists, select

from config.database import get_session
from models.db_models import PendingItemRow
from models.email_models import DraftReply, EmailNodeOutput, PendingItem


def _to_item(row: PendingItemRow) -> PendingItem:
    return PendingItem(
        id=row.id,
        email_id=row.email_id,
        subject=row.subject,
        sender=row.sender,
        draft=DraftReply.model_validate_json(row.draft),
    )


class PendingStore:
    async def add(self, output: EmailNodeOutput) -> str:
        item_id = str(uuid.uuid4())
        async with get_session() as session:
            session.add(
                PendingItemRow(
                    id=item_id,
                    email_id=output.email_id,
                    subject=output.subject,
                    sender=output.sender,
                    draft=output.draft.model_dump_json(),
                )
            )
            await session.commit()
        return item_id

    async def list_all(self) -> list[PendingItem]:
        async with get_session() as session:
            rows = (await session.execute(select(PendingItemRow))).scalars().all()
            return [_to_item(row) for row in rows]

    async def get(self, item_id: str) -> PendingItem | None:
        async with get_session() as session:
            row = await session.get(PendingItemRow, item_id)
            return _to_item(row) if row is not None else None

    async def has_email(self, email_id: str) -> bool:
        async with get_session() as session:
            result = await session.execute(
                select(exists().where(PendingItemRow.email_id == email_id))
            )
            return bool(result.scalar())

    async def remove(self, item_id: str) -> bool:
        async with get_session() as session:
            result = await session.execute(
                delete(PendingItemRow).where(PendingItemRow.id == item_id)
            )
            await session.commit()
            return result.rowcount > 0


pending_store = PendingStore()
