from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import Base


class SessionRow(Base):
    __tablename__ = "session"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_name: Mapped[str | None] = mapped_column(String, nullable=True)
    calendar_action_open: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    messages: Mapped[list["SessionMessageRow"]] = relationship(
        "SessionMessageRow",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="select",
    )


class SessionMessageRow(Base):
    __tablename__ = "session_message"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("session.session_id", ondelete="CASCADE"), nullable=False
    )
    agent_type: Mapped[str] = mapped_column(String(32), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    message_json: Mapped[str] = mapped_column(Text, nullable=False)
    session: Mapped["SessionRow"] = relationship("SessionRow", back_populates="messages")

    __table_args__ = (
        Index("ix_session_message_lookup", "session_id", "agent_type", "sequence"),
    )


class PendingItemRow(Base):
    __tablename__ = "pending_item"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email_id: Mapped[str] = mapped_column(String)
    subject: Mapped[str] = mapped_column(String)
    sender: Mapped[str] = mapped_column(String)
    draft: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SentEmailRow(Base):
    __tablename__ = "sent_email"

    email_id: Mapped[str] = mapped_column(String, primary_key=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
