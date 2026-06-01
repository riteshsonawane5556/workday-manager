import uuid
from models.email_models import PendingItem, EmailNodeOutput


class PendingStore:
    def __init__(self):
        self._store: dict[str, PendingItem] = {}

    def add(self, output: EmailNodeOutput) -> str:
        item_id = str(uuid.uuid4())
        item = PendingItem(
            id=item_id,
            email_id=output.email_id,
            subject=output.subject,
            sender=output.sender,
            draft=output.draft,
        )
        self._store[item_id] = item
        return item_id

    def list_all(self) -> list[PendingItem]:
        return list(self._store.values())

    def get(self, item_id: str) -> PendingItem | None:
        return self._store.get(item_id)

    def has_email(self, email_id: str) -> bool:
        return any(item.email_id == email_id for item in self._store.values())

    def remove(self, item_id: str) -> bool:
        if item_id in self._store:
            del self._store[item_id]
            return True
        return False


pending_store = PendingStore()
