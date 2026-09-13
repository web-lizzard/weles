from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.in_memory.capture.capture_session_repository import (
    InMemoryCaptureSessionRepository,
)
from adapters.out.in_memory.capture.message_repository import InMemoryMessageRepository
from adapters.out.in_memory.capture.message_store import InMemoryMessageStore
from adapters.out.sqlalchemy.capture.capture_session_repository import (
    SqlAlchemyCaptureSessionRepository,
)
from adapters.out.sqlalchemy.capture.message_repository import (
    SqlAlchemyMessageRepository,
)
from adapters.out.sqlalchemy.engine import create_session_factory
from domain.capture.capture_session import CaptureSession
from domain.capture.message import Message
from domain.capture.ports import CaptureSessionRepository, MessageRepository
from domain.capture.value_objects import (
    MessageContent,
    MessageId,
    MessageRole,
    SessionId,
)


class _CommittingCaptureSessionRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def get(self, session_id: SessionId) -> CaptureSession | None:
        async with self._session_factory() as db_session:
            return await SqlAlchemyCaptureSessionRepository(db_session).get(session_id)

    async def save(self, session: CaptureSession) -> None:
        async with self._session_factory() as db_session:
            await SqlAlchemyCaptureSessionRepository(db_session).save(session)
            await db_session.commit()


class _CommittingMessageRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def add(self, message: Message) -> None:
        async with self._session_factory() as db_session:
            await SqlAlchemyMessageRepository(db_session).add(message)
            await db_session.commit()

    async def history(self, session_id: SessionId) -> list[Message]:
        async with self._session_factory() as db_session:
            return await SqlAlchemyMessageRepository(db_session).history(session_id)


@dataclass
class _MessageFixture:
    repository: MessageRepository
    session_repository: CaptureSessionRepository
    make_repository: Callable[[], MessageRepository] | None


def _make_in_memory_fixture() -> _MessageFixture:
    store = InMemoryMessageStore()

    def make_repository() -> InMemoryMessageRepository:
        return InMemoryMessageRepository(store)

    return _MessageFixture(
        repository=InMemoryMessageRepository(store),
        session_repository=InMemoryCaptureSessionRepository(),
        make_repository=make_repository,
    )


@pytest.fixture(
    params=["in_memory", pytest.param("postgres", marks=pytest.mark.postgres)]
)
def message_fixture(request: pytest.FixtureRequest) -> _MessageFixture:
    if request.param == "in_memory":  # pyright: ignore[reportAny]
        return _make_in_memory_fixture()
    engine: AsyncEngine = request.getfixturevalue("engine")  # pyright: ignore[reportAny]
    session_factory = create_session_factory(engine)
    return _MessageFixture(
        repository=_CommittingMessageRepository(session_factory),
        session_repository=_CommittingCaptureSessionRepository(session_factory),
        make_repository=None,
    )


async def test_added_message_is_in_history_read_through_another_repository_instance(
    message_fixture: _MessageFixture,
) -> None:
    capture_session = CaptureSession.start()
    await message_fixture.session_repository.save(capture_session)
    message = Message.record(
        session_id=capture_session.id,
        role=MessageRole.USER,
        content=MessageContent(value="Let's talk about TCP handshakes"),
    )
    if message_fixture.make_repository is not None:
        writer = message_fixture.make_repository()
        reader = message_fixture.make_repository()
    else:
        writer = message_fixture.repository
        reader = message_fixture.repository

    await writer.add(message)

    history = await reader.history(message.session_id)

    assert history == [message]


async def test_history_returns_messages_for_session_in_order(
    message_fixture: _MessageFixture,
) -> None:
    capture_session = CaptureSession.start()
    await message_fixture.session_repository.save(capture_session)
    session_id = capture_session.id
    first = Message.record(
        session_id=session_id,
        role=MessageRole.USER,
        content=MessageContent(value="First"),
    )
    second = Message.record(
        session_id=session_id,
        role=MessageRole.AGENT,
        content=MessageContent(value="Second"),
    )
    other_session = CaptureSession.start()
    await message_fixture.session_repository.save(other_session)
    other_session_message = Message.record(
        session_id=other_session.id,
        role=MessageRole.USER,
        content=MessageContent(value="Other"),
    )

    repository = message_fixture.repository
    await repository.add(first)
    await repository.add(second)
    await repository.add(other_session_message)

    history = await repository.history(session_id)

    assert history == [first, second]


async def test_history_orders_by_insertion_when_created_at_is_equal(
    message_fixture: _MessageFixture,
) -> None:
    capture_session = CaptureSession.start()
    await message_fixture.session_repository.save(capture_session)
    session_id = capture_session.id
    shared_created_at = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    first = Message(
        id=MessageId.new(),
        session_id=session_id,
        role=MessageRole.USER,
        content=MessageContent(value="First"),
        created_at=shared_created_at,
    )
    second = Message(
        id=MessageId.new(),
        session_id=session_id,
        role=MessageRole.AGENT,
        content=MessageContent(value="Second"),
        created_at=shared_created_at,
    )

    repository = message_fixture.repository
    await repository.add(first)
    await repository.add(second)

    history = await repository.history(session_id)

    assert history == [first, second]


async def test_history_returns_empty_list_when_session_has_no_messages(
    message_fixture: _MessageFixture,
) -> None:
    assert await message_fixture.repository.history(SessionId.new()) == []
