import asyncio
from datetime import datetime
from typing import List

from config.nylas_client import nylas, NYLAS_GRANT_ID
from models.email_models import EmailMeta


def _build_email_meta(msg, is_unread: bool) -> EmailMeta:
    sender = ""
    if msg.from_:
        first = msg.from_[0]
        sender = first.get("email") or first.get("name", "")
    date_str = ""
    if msg.date:
        date_str = datetime.fromtimestamp(msg.date).strftime("%Y-%m-%d %H:%M")
    return EmailMeta(
        id=msg.id,
        subject=msg.subject or "(no subject)",
        sender=sender,
        date=date_str,
        snippet=msg.snippet or "",
        is_unread=is_unread,
        thread_id=getattr(msg, "thread_id", None),
    )


def _fetch_messages(n: int) -> List[EmailMeta]:
    unread_resp = nylas.messages.list(
        NYLAS_GRANT_ID,
        query_params={"limit": n, "unread": True},
    )
    read_resp = nylas.messages.list(
        NYLAS_GRANT_ID,
        query_params={"limit": n, "unread": False},
    )
    seen_ids: set[str] = set()
    emails: List[EmailMeta] = []
    for msg in unread_resp.data:
        emails.append(_build_email_meta(msg, is_unread=True))
        seen_ids.add(msg.id)
    for msg in read_resp.data:
        if msg.id not in seen_ids:
            emails.append(_build_email_meta(msg, is_unread=False))
    return emails


async def list_emails(n: int = 10) -> List[EmailMeta]:
    return await asyncio.to_thread(_fetch_messages, n)


def _fetch_body(email_id: str) -> str:
    response = nylas.messages.find(NYLAS_GRANT_ID, email_id)
    return response.data.body or ""


async def fetch_email_body(email_id: str) -> str:
    return await asyncio.to_thread(_fetch_body, email_id)


def _mark_read(email_id: str) -> None:
    nylas.messages.update(
        NYLAS_GRANT_ID,
        email_id,
        request_body={"unread": False},
    )


async def mark_email_read(email_id: str) -> None:
    await asyncio.to_thread(_mark_read, email_id)


def _fetch_thread_messages(thread_id: str) -> list[dict]:
    response = nylas.messages.list(
        NYLAS_GRANT_ID,
        query_params={"thread_id": thread_id, "limit": 10},
    )
    result = []
    for msg in response.data:
        sender = ""
        if msg.from_:
            first = msg.from_[0]
            sender = first.get("email") or first.get("name", "")
        date_str = ""
        if msg.date:
            date_str = datetime.fromtimestamp(msg.date).strftime("%Y-%m-%d %H:%M")
        result.append({
            "id": msg.id,
            "sender": sender,
            "date": date_str,
            "body": msg.body or msg.snippet or "",
        })
    return result


async def fetch_thread(thread_id: str) -> list[dict]:
    return await asyncio.to_thread(_fetch_thread_messages, thread_id)
