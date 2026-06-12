import asyncio
import uuid

from models.email_models import DraftReply, EmailNodeOutput, PendingItem
from models.db_models import PendingItemRow
import repository.pending_repository as pending_repo
from config.nylas_client import nylas, NYLAS_GRANT_ID
from tools.email_tools import mark_email_read


def _row_to_item(row: PendingItemRow) -> PendingItem:
    return PendingItem(
        id=row.id,
        email_id=row.email_id,
        subject=row.subject,
        sender=row.sender,
        draft=DraftReply.model_validate_json(row.draft),
    )


async def add_pending_item(output: EmailNodeOutput) -> str:
    item_id = str(uuid.uuid4())
    await pending_repo.insert_pending_item(
        item_id=item_id,
        email_id=output.email_id,
        subject=output.subject,
        sender=output.sender,
        draft_json=output.draft.model_dump_json(),
    )
    return item_id


async def list_pending_items() -> list[PendingItem]:
    rows = await pending_repo.list_pending_items()
    return [_row_to_item(row) for row in rows]


async def get_pending_item(item_id: str) -> PendingItem | None:
    row = await pending_repo.get_pending_item(item_id)
    return _row_to_item(row) if row is not None else None


async def email_already_pending(email_id: str) -> bool:
    return await pending_repo.pending_email_exists(email_id)


async def remove_pending_item(item_id: str) -> bool:
    return await pending_repo.delete_pending_item(item_id) > 0


async def send_approved_email(item: PendingItem) -> None:
    await asyncio.to_thread(
        nylas.messages.send,
        NYLAS_GRANT_ID,
        {"subject": item.draft.subject, "body": item.draft.body, "to": [{"email": item.draft.to}]},
    )
    if item.email_id:
        await mark_email_read(item.email_id)
