from models.email_models import EmailNodeOutput, PendingItem
from services.pending_service import (
    add_pending_item,
    list_pending_items,
    get_pending_item,
    email_already_pending,
    remove_pending_item,
)


class PendingStore:
    async def add(self, output: EmailNodeOutput) -> str:
        return await add_pending_item(output)

    async def list_all(self) -> list[PendingItem]:
        return await list_pending_items()

    async def get(self, item_id: str) -> PendingItem | None:
        return await get_pending_item(item_id)

    async def has_email(self, email_id: str) -> bool:
        return await email_already_pending(email_id)

    async def remove(self, item_id: str) -> bool:
        return await remove_pending_item(item_id)


pending_store = PendingStore()
