import asyncio
from models.email_models import PendingItem
from config.nylas_client import nylas, NYLAS_GRANT_ID
from tools.email_tools import mark_email_read


async def send_approved_email(item: PendingItem) -> None:
    await asyncio.to_thread(
        nylas.messages.send,
        NYLAS_GRANT_ID,
        {"subject": item.draft.subject, "body": item.draft.body, "to": [{"email": item.draft.to}]},
    )
    await mark_email_read(item.email_id)
