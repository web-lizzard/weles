from uuid import UUID

from domain.capture.message import Message
from domain.capture.value_objects import SessionId


class InMemoryMessageStore:
    def __init__(self) -> None:
        self._messages: dict[UUID, list[Message]] = {}

    def add(self, message: Message) -> None:
        self._messages.setdefault(message.session_id.value, []).append(message)

    def list_by_session(self, session_id: SessionId) -> list[Message]:
        return self._messages.get(session_id.value, [])
