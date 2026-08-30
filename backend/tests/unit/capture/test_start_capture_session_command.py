from uuid import UUID

from adapters.out.in_memory.capture.capture_session_repository import (
    InMemoryCaptureSessionRepository,
)
from adapters.out.in_memory.capture.message_repository import (
    InMemoryMessageRepository,
)
from adapters.out.in_memory.capture.message_store import InMemoryMessageStore
from adapters.out.in_memory.capture.unit_of_work import InMemoryUnitOfWork
from application.capture.commands.start_capture_session import (
    StartCaptureSessionCommand,
)
from domain.capture.value_objects import SessionId, SessionStatus


async def test_handle_creates_and_persists_bare_session() -> None:
    store = InMemoryMessageStore()
    session_repo = InMemoryCaptureSessionRepository()
    message_repo = InMemoryMessageRepository(store)
    uow = InMemoryUnitOfWork(session_repo, message_repo)
    command = StartCaptureSessionCommand(uow)  # pyright: ignore[reportArgumentType]

    response = await command.handle()

    assert isinstance(response.session_id, UUID)
    persisted = await session_repo.get(SessionId(value=response.session_id))
    assert persisted is not None
    assert persisted.topic is None
    assert persisted.status == SessionStatus.OPEN
