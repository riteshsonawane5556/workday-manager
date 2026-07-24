from dataclasses import dataclass, field

from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter, ModelRequest

import repository.session_repository as session_repo
import repository.session_event_repository as event_repo
from models.orchestrator_models import RecentEvent


@dataclass
class UnifiedHistory:
    manager: list[ModelMessage] = field(default_factory=list)
    calendar_action: list[ModelMessage] = field(default_factory=list)
    recent_events: list[RecentEvent] = field(default_factory=list)
    calendar_action_open: bool = False


def _dump_one(msg: ModelMessage) -> str:
    return ModelMessagesTypeAdapter.dump_json([msg]).decode("utf-8")


def _load_one(raw: str) -> ModelMessage:
    return ModelMessagesTypeAdapter.validate_json(raw)[0]


def _derive_session_name(messages: list[ModelMessage]) -> str | None:
    from pydantic_ai.messages import UserPromptPart
    for msg in messages:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, UserPromptPart) and isinstance(part.content, str):
                    return part.content[:80].strip() or None
    return None


async def get_unified(session_id: str) -> UnifiedHistory:
    session_row = await session_repo.get_session_row(session_id)
    if session_row is None:
        return UnifiedHistory()

    manager_rows = await session_repo.fetch_agent_messages(session_id, "manager")
    calendar_rows = await session_repo.fetch_agent_messages(session_id, "calendar_action")
    event_dicts = await event_repo.fetch_session_events(session_id)

    recent_events = [
        RecentEvent(
            id=e["id"],
            title=e["title"],
            start_unix=e["start_unix"],
            end_unix=e["end_unix"],
            attendees=e.get("attendees", []),
        )
        for e in event_dicts
    ]

    return UnifiedHistory(
        manager=[_load_one(r.message_json) for r in manager_rows],
        calendar_action=[_load_one(r.message_json) for r in calendar_rows],
        recent_events=recent_events,
        calendar_action_open=session_row.calendar_action_open,
    )


async def save_unified(
    session_id: str,
    manager_msgs: list[ModelMessage],
    calendar_msgs: list[ModelMessage],
    recent_events: list[RecentEvent],
    calendar_action_open: bool = False,
) -> None:
    session_name = _derive_session_name(manager_msgs)

    messages_by_agent: dict[str, list[tuple[int, str, str]]] = {
        "manager": [(seq, msg.kind, _dump_one(msg)) for seq, msg in enumerate(manager_msgs)],
        "calendar_action": [(seq, msg.kind, _dump_one(msg)) for seq, msg in enumerate(calendar_msgs)],
    }

    await session_repo.upsert_session(
        session_id=session_id,
        calendar_action_open=calendar_action_open,
        session_name=session_name,
        messages_by_agent=messages_by_agent,
    )

    event_dicts = [
        {
            "id": e.id,
            "title": e.title,
            "start_unix": e.start_unix,
            "end_unix": e.end_unix,
            "attendees": e.attendees,
        }
        for e in recent_events
    ]
    await event_repo.upsert_session_events(session_id, event_dicts)


async def clear_session(session_id: str) -> None:
    await session_repo.delete_session(session_id)
