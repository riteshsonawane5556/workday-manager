from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from config.database import Base


class SessionHistoryRow(Base):
    __tablename__ = "session_history"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    planner: Mapped[str] = mapped_column(Text, default="[]")
    calendar_action: Mapped[str] = mapped_column(Text, default="[]")
    synthesize: Mapped[str] = mapped_column(Text, default="[]")
    calendar_action_open: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class PendingItemRow(Base):
    __tablename__ = "pending_item"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email_id: Mapped[str] = mapped_column(String)
    subject: Mapped[str] = mapped_column(String)
    sender: Mapped[str] = mapped_column(String)
    draft: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
