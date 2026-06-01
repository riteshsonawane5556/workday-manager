from pydantic import BaseModel
from typing import List


class EmailMeta(BaseModel):
    id: str
    subject: str
    sender: str
    date: str
    snippet: str
    is_unread: bool


class AgentResponse(BaseModel):
    summary: str
    emails: List[EmailMeta]


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
