from dataclasses import dataclass, field
from pydantic_ai.messages import ModelMessage


@dataclass
class SessionHistory:
    planner: list[ModelMessage] = field(default_factory=list)
    calendar_action: list[ModelMessage] = field(default_factory=list)
    synthesize: list[ModelMessage] = field(default_factory=list)
    calendar_action_open: bool = False


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionHistory] = {}

    def get(self, session_id: str) -> SessionHistory:
        return self._sessions.get(session_id, SessionHistory())

    def set(self, session_id: str, history: SessionHistory) -> None:
        self._sessions[session_id] = history

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


session_store = SessionStore()
