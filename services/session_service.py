from dataclasses import dataclass, field

from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter, ModelRequest

import repository.session_repository as session_repo


@dataclass
class SessionHistory:
    planner: list[ModelMessage] = field(default_factory=list)
    calendar_action: list[ModelMessage] = field(default_factory=list)
    synthesize: list[ModelMessage] = field(default_factory=list)
    calendar_action_open: bool = False


def _dump_one(msg: ModelMessage) -> str:
    return ModelMessagesTypeAdapter.dump_json([msg]).decode("utf-8")


def _load_one(raw: str) -> ModelMessage:
    return ModelMessagesTypeAdapter.validate_json(raw)[0]


def _derive_session_name(planner_messages: list[ModelMessage]) -> str | None:
    from pydantic_ai.messages import UserPromptPart
    for msg in planner_messages:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, UserPromptPart) and isinstance(part.content, str):
                    return part.content[:80].strip() or None
    return None


async def get_session_history(session_id: str) -> SessionHistory:
    session_row = await session_repo.get_session_row(session_id)
    if session_row is None:
        return SessionHistory()

    planner_rows = await session_repo.fetch_agent_messages(session_id, "planner")
    calendar_rows = await session_repo.fetch_agent_messages(session_id, "calendar_action")
    synthesize_rows = await session_repo.fetch_agent_messages(session_id, "synthesize")

    return SessionHistory(
        planner=[_load_one(r.message_json) for r in planner_rows],
        calendar_action=[_load_one(r.message_json) for r in calendar_rows],
        synthesize=[_load_one(r.message_json) for r in synthesize_rows],
        calendar_action_open=session_row.calendar_action_open,
    )


async def save_session_history(session_id: str, history: SessionHistory) -> None:
    session_name = _derive_session_name(history.planner)

    agent_map: dict[str, list[ModelMessage]] = {
        "planner": history.planner,
        "calendar_action": history.calendar_action,
        "synthesize": history.synthesize,
    }
    messages_by_agent: dict[str, list[tuple[int, str, str]]] = {
        agent_type: [
            (seq, msg.kind, _dump_one(msg))
            for seq, msg in enumerate(messages)
        ]
        for agent_type, messages in agent_map.items()
    }

    await session_repo.upsert_session(
        session_id=session_id,
        calendar_action_open=history.calendar_action_open,
        session_name=session_name,
        messages_by_agent=messages_by_agent,
    )


async def clear_session(session_id: str) -> None:
    await session_repo.delete_session(session_id)
