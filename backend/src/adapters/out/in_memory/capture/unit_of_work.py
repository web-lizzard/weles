from uuid import UUID

from adapters.out.in_memory.capture.capture_session_repository import (
    InMemoryCaptureSessionRepository,
)
from adapters.out.in_memory.capture.message_repository import (
    InMemoryMessageRepository,
)
from adapters.out.in_memory.capture.message_store import InMemoryMessageStore
from domain.capture.capture_session import CaptureSession
from domain.capture.message import Message


class InMemoryUnitOfWork:
    capture_sessions: InMemoryCaptureSessionRepository
    messages: InMemoryMessageRepository

    def __init__(
        self,
        capture_sessions: InMemoryCaptureSessionRepository,
        messages: InMemoryMessageRepository,
        message_store: InMemoryMessageStore,
    ) -> None:
        self.capture_sessions = capture_sessions
        self.messages = messages
        self._message_store: InMemoryMessageStore = message_store
        self._committed: bool = False
        self._sessions_snapshot: dict[UUID, CaptureSession] = {}
        self._messages_snapshot: dict[UUID, list[Message]] = {}

    async def __aenter__(self) -> "InMemoryUnitOfWork":
        self._committed = False
        self._sessions_snapshot = self.capture_sessions.snapshot()
        self._messages_snapshot = self._message_store.snapshot()
        return self

    async def __aexit__(self, *exc: object) -> None:
        if not self._committed:
            self.capture_sessions.restore(self._sessions_snapshot)
            self._message_store.restore(self._messages_snapshot)

    async def commit(self) -> None:
        self._committed = True
