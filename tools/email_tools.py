import asyncio
from datetime import datetime
from typing import List

from config.nylas_client import nylas, NYLAS_GRANT_ID
from models.email_models import EmailMeta


def _fetch_messages(n: int) -> List[EmailMeta]:
    response = nylas.messages.list(
        NYLAS_GRANT_ID,
        query_params={"limit": n, "unread": True},
    )
    emails: List[EmailMeta] = []
    for msg in response.data:
        sender = ""
        if msg.from_:
            first = msg.from_[0]
            sender = first.get("name") or first.get("email", "")

        date_str = ""
        if msg.date:
            date_str = datetime.fromtimestamp(msg.date).strftime("%Y-%m-%d %H:%M")

        emails.append(
            EmailMeta(
                id=msg.id,
                subject=msg.subject or "(no subject)",
                sender=sender,
                date=date_str,
                snippet=msg.snippet or "",
                is_unread=True,
            )
        )
    return emails


async def list_emails(n: int = 10) -> List[EmailMeta]:
    """Fetch the n most recent unread emails from the connected inbox."""
    return await asyncio.to_thread(_fetch_messages, n)
