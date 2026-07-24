from pydantic import BaseModel
from typing import List, Literal


class EmailMeta(BaseModel):
    id: str
    subject: str
    sender: str
    date: str
    snippet: str
    is_unread: bool
    thread_id: str | None = None


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


class EmailClassification(BaseModel):
    label: Literal["urgent", "fyi", "actionable"]
    reasoning: str


class DraftReply(BaseModel):
    subject: str
    body: str
    to: str


class EmailNodeOutput(BaseModel):
    email_id: str
    subject: str
    sender: str
    classification: EmailClassification
    draft: DraftReply | None = None


class PendingItem(BaseModel):
    id: str
    email_id: str
    subject: str
    sender: str
    draft: DraftReply


class ProcessingResult(BaseModel):
    processed: int
    actionable: int
    pending_ids: list[str]
