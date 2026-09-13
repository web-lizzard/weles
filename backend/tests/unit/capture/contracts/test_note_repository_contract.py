from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.in_memory.capture.capture_session_repository import (
    InMemoryCaptureSessionRepository,
)
from adapters.out.in_memory.capture.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.capture.tag_repository import InMemoryTagRepository
from adapters.out.in_memory.capture.topic_repository import InMemoryTopicRepository
from adapters.out.sqlalchemy.capture.capture_session_repository import (
    SqlAlchemyCaptureSessionRepository,
)
from adapters.out.sqlalchemy.capture.note_repository import SqlAlchemyNoteRepository
from adapters.out.sqlalchemy.capture.tag_repository import SqlAlchemyTagRepository
from adapters.out.sqlalchemy.capture.topic_repository import SqlAlchemyTopicRepository
from adapters.out.sqlalchemy.engine import create_session_factory
from domain.capture.capture_session import CaptureSession
from domain.capture.note import Note
from domain.capture.ports import NoteRepository
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import (
    Embedding,
    Label,
    NoteContent,
    NoteId,
    NoteStatus,
    SessionId,
    TagId,
    TopicId,
)

_EMBEDDING_MODEL = "test"


class _CommittingCaptureSessionRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def save(self, session: CaptureSession) -> None:
        async with self._session_factory() as db_session:
            await SqlAlchemyCaptureSessionRepository(db_session).save(session)
            await db_session.commit()


class _CommittingNoteRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def add(self, note: Note) -> None:
        async with self._session_factory() as db_session:
            await SqlAlchemyNoteRepository(db_session).add(note)
            await db_session.commit()

    async def get(self, note_id: NoteId) -> Note | None:
        async with self._session_factory() as db_session:
            return await SqlAlchemyNoteRepository(db_session).get(note_id)


class _CommittingTopicRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def add(self, topic: Topic) -> None:
        async with self._session_factory() as db_session:
            await SqlAlchemyTopicRepository(db_session).add(topic)
            await db_session.commit()


class _CommittingTagRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def add(self, tag: Tag) -> None:
        async with self._session_factory() as db_session:
            await SqlAlchemyTagRepository(db_session).add(tag)
            await db_session.commit()


class _NoteSeed(Protocol):
    async def persist(self, note: Note, topic: Topic, tags: list[Tag]) -> None: ...


@dataclass
class _NoteFixture:
    repository: NoteRepository
    seed: _NoteSeed


class _InMemorySeed:
    def __init__(
        self,
        sessions: InMemoryCaptureSessionRepository,
        topics: InMemoryTopicRepository,
        tags: InMemoryTagRepository,
    ) -> None:
        self._sessions: InMemoryCaptureSessionRepository = sessions
        self._topics: InMemoryTopicRepository = topics
        self._tags: InMemoryTagRepository = tags

    async def persist(self, note: Note, topic: Topic, tags: list[Tag]) -> None:
        session = CaptureSession.start().model_copy(update={"id": note.session_id})
        await self._sessions.save(session)
        await self._topics.add(topic)
        for tag in tags:
            await self._tags.add(tag)


class _PostgresSeed:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sessions: _CommittingCaptureSessionRepository = (
            _CommittingCaptureSessionRepository(session_factory)
        )
        self._topics: _CommittingTopicRepository = _CommittingTopicRepository(
            session_factory
        )
        self._tags: _CommittingTagRepository = _CommittingTagRepository(session_factory)

    async def persist(self, note: Note, topic: Topic, tags: list[Tag]) -> None:
        session = CaptureSession.start().model_copy(update={"id": note.session_id})
        await self._sessions.save(session)
        await self._topics.add(topic)
        for tag in tags:
            await self._tags.add(tag)


def _sample_note_parts() -> tuple[Note, Topic, list[Tag]]:
    topic = Topic(
        id=TopicId.new(),
        label=Label(value="TCP handshakes"),
        embedding=Embedding(model=_EMBEDDING_MODEL, values=(0.1, 0.2)),
        created_at=datetime.now(UTC),
    )
    tag = Tag(
        id=TagId.new(),
        label=Label(value="networking"),
        embedding=Embedding(model=_EMBEDDING_MODEL, values=(0.3, 0.4)),
        created_at=datetime.now(UTC),
    )
    note = Note(
        id=NoteId.new(),
        session_id=SessionId.new(),
        topic_id=topic.id,
        content=NoteContent(value="We discussed how connections are established."),
        tag_ids=[tag.id],
        status=NoteStatus.DRAFT,
        created_at=datetime.now(UTC),
        approved_at=None,
    )
    return note, topic, [tag]


@pytest.fixture(
    params=["in_memory", pytest.param("postgres", marks=pytest.mark.postgres)]
)
def note_fixture(request: pytest.FixtureRequest) -> _NoteFixture:
    if request.param == "in_memory":  # pyright: ignore[reportAny]
        topics = InMemoryTopicRepository()
        tags = InMemoryTagRepository()
        sessions = InMemoryCaptureSessionRepository()
        return _NoteFixture(
            repository=InMemoryNoteRepository(),
            seed=_InMemorySeed(sessions, topics, tags),
        )
    engine: AsyncEngine = request.getfixturevalue("engine")  # pyright: ignore[reportAny]
    session_factory = create_session_factory(engine)
    return _NoteFixture(
        repository=_CommittingNoteRepository(session_factory),
        seed=_PostgresSeed(session_factory),
    )


async def test_add_then_get_returns_the_saved_note(note_fixture: _NoteFixture) -> None:
    note, topic, tags = _sample_note_parts()
    await note_fixture.seed.persist(note, topic, tags)

    await note_fixture.repository.add(note)
    result = await note_fixture.repository.get(note.id)

    assert result == note


async def test_get_returns_none_for_unknown_note_id(note_fixture: _NoteFixture) -> None:
    result = await note_fixture.repository.get(NoteId.new())

    assert result is None


async def test_second_add_with_same_id_overwrites(note_fixture: _NoteFixture) -> None:
    note, topic, tags = _sample_note_parts()
    await note_fixture.seed.persist(note, topic, tags)
    updated = note.model_copy(
        update={"content": NoteContent(value="Updated body text.")}
    )

    await note_fixture.repository.add(note)
    await note_fixture.repository.add(updated)
    result = await note_fixture.repository.get(note.id)

    assert result == updated


async def test_second_add_reorders_tag_ids(note_fixture: _NoteFixture) -> None:
    topic = Topic(
        id=TopicId.new(),
        label=Label(value="TCP handshakes"),
        embedding=Embedding(model=_EMBEDDING_MODEL, values=(0.1, 0.2)),
        created_at=datetime.now(UTC),
    )
    first_tag = Tag(
        id=TagId.new(),
        label=Label(value="alpha"),
        embedding=Embedding(model=_EMBEDDING_MODEL, values=(0.3, 0.4)),
        created_at=datetime.now(UTC),
    )
    second_tag = Tag(
        id=TagId.new(),
        label=Label(value="beta"),
        embedding=Embedding(model=_EMBEDDING_MODEL, values=(0.5, 0.6)),
        created_at=datetime.now(UTC),
    )
    note = Note(
        id=NoteId.new(),
        session_id=SessionId.new(),
        topic_id=topic.id,
        content=NoteContent(value="Tagged note."),
        tag_ids=[first_tag.id, second_tag.id],
        status=NoteStatus.DRAFT,
        created_at=datetime.now(UTC),
        approved_at=None,
    )
    await note_fixture.seed.persist(note, topic, [first_tag, second_tag])

    await note_fixture.repository.add(note)
    reordered = note.model_copy(update={"tag_ids": [second_tag.id, first_tag.id]})
    await note_fixture.repository.add(reordered)
    result = await note_fixture.repository.get(note.id)

    assert result is not None
    assert result.tag_ids == [second_tag.id, first_tag.id]
