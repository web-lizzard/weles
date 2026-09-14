from uuid import UUID

from adapters.out.in_memory.capture.capture_session_repository import (
    InMemoryCaptureSessionRepository,
)
from adapters.out.in_memory.capture.message_repository import (
    InMemoryMessageRepository,
)
from adapters.out.in_memory.capture.message_store import InMemoryMessageStore
from adapters.out.in_memory.capture.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.capture.note_vocabulary_repository import (
    InMemoryNoteVocabularyRepository,
)
from adapters.out.in_memory.capture.tag_repository import InMemoryTagRepository
from adapters.out.in_memory.capture.topic_repository import InMemoryTopicRepository
from adapters.out.in_memory.capture.unit_of_work import InMemoryUnitOfWork
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from application.capture.commands.start_capture_session import (
    StartCaptureSessionCommand,
)
from domain.capture.value_objects import SessionId, SessionStatus
from domain.shared.identity.model import UserId


async def test_handle_creates_and_persists_bare_session() -> None:
    store = InMemoryMessageStore()
    session_repo = InMemoryCaptureSessionRepository()
    message_repo = InMemoryMessageRepository(store)
    outbox_store = InMemoryOutboxStore()
    topics = InMemoryTopicRepository()
    tags = InMemoryTagRepository()
    uow = InMemoryUnitOfWork(
        session_repo,
        message_repo,
        store,
        InMemoryNoteRepository(),
        topics,
        tags,
        InMemoryNoteVocabularyRepository(topics, tags),
        outbox_store,
        InMemoryOutboxAppender(outbox_store),
    )
    command = StartCaptureSessionCommand(uow)  # pyright: ignore[reportArgumentType]

    response = await command.handle(UserId.new())

    assert isinstance(response.session_id, UUID)
    persisted = await session_repo.get(SessionId(value=response.session_id))
    assert persisted is not None
    assert persisted.topic is None
    assert persisted.status == SessionStatus.OPEN
