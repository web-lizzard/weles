from adapters.out.in_memory.capture.capture_session_repository import (
    InMemoryCaptureSessionRepository,
)
from adapters.out.in_memory.capture.message_repository import (
    InMemoryMessageRepository,
)


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

    async def __aenter__(self) -> "InMemoryUnitOfWork":
        raise NotImplementedError

    async def __aexit__(self, *exc: object) -> None:
        raise NotImplementedError

    async def commit(self) -> None:
        raise NotImplementedError
