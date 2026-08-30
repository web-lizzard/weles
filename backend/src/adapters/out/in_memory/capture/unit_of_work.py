import copy
from uuid import UUID

from adapters.out.in_memory.capture.capture_session_repository import (
    InMemoryCaptureSessionRepository,
)
from adapters.out.in_memory.capture.message_repository import (
    InMemoryMessageRepository,
)
from domain.capture.capture_session import CaptureSession
from domain.capture.message import Message


class InMemoryUnitOfWork:
    capture_sessions: InMemoryCaptureSessionRepository
    messages: InMemoryMessageRepository

    def __init__(
        self,
        capture_sessions: InMemoryCaptureSessionRepository,
        messages: InMemoryMessageRepository,
    ) -> None:
        self.capture_sessions = capture_sessions
        self.messages = messages
        self._committed: bool = False
        self._sessions_snapshot: dict[UUID, CaptureSession] = {}
        self._messages_snapshot: dict[UUID, list[Message]] = {}

    async def __aenter__(self) -> "InMemoryUnitOfWork":
        self._committed = False
        self._sessions_snapshot = copy.deepcopy(self.capture_sessions._sessions)  # pyright: ignore[reportPrivateUsage]
        self._messages_snapshot = copy.deepcopy(self.messages._store._messages)  # pyright: ignore[reportPrivateUsage]
        return self

    async def __aexit__(self, *exc: object) -> None:
        if not self._committed:
            self.capture_sessions._sessions = self._sessions_snapshot  # pyright: ignore[reportPrivateUsage]
            self.messages._store._messages = self._messages_snapshot  # pyright: ignore[reportPrivateUsage]

    async def commit(self) -> None:
        self._committed = True
