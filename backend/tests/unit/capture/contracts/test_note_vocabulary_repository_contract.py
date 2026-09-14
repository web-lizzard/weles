from dataclasses import dataclass

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.in_memory.capture.note_vocabulary_repository import (
    InMemoryNoteVocabularyRepository,
)
from adapters.out.in_memory.capture.tag_repository import InMemoryTagRepository
from adapters.out.in_memory.capture.topic_repository import InMemoryTopicRepository
from adapters.out.sqlalchemy.capture.note_vocabulary_repository import (
    SqlAlchemyNoteVocabularyRepository,
)
from adapters.out.sqlalchemy.capture.tag_repository import SqlAlchemyTagRepository
from adapters.out.sqlalchemy.capture.topic_repository import SqlAlchemyTopicRepository
from adapters.out.sqlalchemy.engine import create_session_factory
from domain.capture.exceptions import NoteVocabularyIncompleteError
from domain.capture.note import Note
from domain.capture.ports import NoteVocabularyRepository
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import (
    Embedding,
    Label,
    NoteContent,
    SessionId,
    TagId,
)
from domain.shared.identity.model import UserId

_EMBEDDING_MODEL = "test"
_OWNER = UserId.new()


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


class _CommittingNoteVocabularyRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def resolve(self, note: Note):
        async with self._session_factory() as db_session:
            return await SqlAlchemyNoteVocabularyRepository(db_session).resolve(note)


@dataclass
class _VocabularyFixture:
    topics: InMemoryTopicRepository | _CommittingTopicRepository
    tags: InMemoryTagRepository | _CommittingTagRepository
    repository: NoteVocabularyRepository


def _make_in_memory_fixture() -> _VocabularyFixture:
    topics = InMemoryTopicRepository()
    tags = InMemoryTagRepository()
    return _VocabularyFixture(
        topics=topics,
        tags=tags,
        repository=InMemoryNoteVocabularyRepository(topics, tags),
    )


@pytest.fixture(
    params=["in_memory", pytest.param("postgres", marks=pytest.mark.postgres)]
)
def vocabulary_fixture(request: pytest.FixtureRequest) -> _VocabularyFixture:
    if request.param == "in_memory":  # pyright: ignore[reportAny]
        return _make_in_memory_fixture()
    engine: AsyncEngine = request.getfixturevalue("engine")  # pyright: ignore[reportAny]
    session_factory = create_session_factory(engine)
    topics = _CommittingTopicRepository(session_factory)
    tags = _CommittingTagRepository(session_factory)
    return _VocabularyFixture(
        topics=topics,
        tags=tags,
        repository=_CommittingNoteVocabularyRepository(session_factory),
    )


def _sample_topic() -> Topic:
    return Topic.mint(
        _OWNER,
        Label(value="TCP handshakes"),
        Embedding(model=_EMBEDDING_MODEL, values=(0.1, 0.2)),
    )


def _sample_tag() -> Tag:
    return Tag.mint(
        _OWNER,
        Label(value="networking"),
        Embedding(model=_EMBEDDING_MODEL, values=(0.3, 0.4)),
    )


def _note_for(topic: Topic, tags: list[Tag]) -> Note:
    return Note.draft(
        owner_id=_OWNER,
        session_id=SessionId.new(),
        topic=topic,
        content=NoteContent(value="We discussed how connections are established."),
        tags=tags,
    )


async def test_resolve_returns_topic_and_tags_when_all_references_exist(
    vocabulary_fixture: _VocabularyFixture,
) -> None:
    topic = _sample_topic()
    tag = _sample_tag()
    note = _note_for(topic, [tag])
    await vocabulary_fixture.topics.add(topic)
    await vocabulary_fixture.tags.add(tag)

    vocabulary = await vocabulary_fixture.repository.resolve(note)

    assert vocabulary.topic == topic
    assert vocabulary.tags == [tag]


async def test_resolve_raises_when_topic_is_missing(
    vocabulary_fixture: _VocabularyFixture,
) -> None:
    topic = _sample_topic()
    tag = _sample_tag()
    note = _note_for(topic, [tag])
    await vocabulary_fixture.tags.add(tag)

    with pytest.raises(NoteVocabularyIncompleteError):
        _ = await vocabulary_fixture.repository.resolve(note)


async def test_resolve_raises_when_a_tag_is_missing(
    vocabulary_fixture: _VocabularyFixture,
) -> None:
    topic = _sample_topic()
    present_tag = _sample_tag()
    missing_tag_id = TagId.new()
    note = _note_for(topic, [present_tag]).model_copy(
        update={"tag_ids": [present_tag.id, missing_tag_id]}
    )
    await vocabulary_fixture.topics.add(topic)
    await vocabulary_fixture.tags.add(present_tag)

    with pytest.raises(NoteVocabularyIncompleteError):
        _ = await vocabulary_fixture.repository.resolve(note)


async def test_resolve_returns_empty_tags_when_note_has_no_tag_ids(
    vocabulary_fixture: _VocabularyFixture,
) -> None:
    topic = _sample_topic()
    note = _note_for(topic, [])
    await vocabulary_fixture.topics.add(topic)

    vocabulary = await vocabulary_fixture.repository.resolve(note)

    assert vocabulary.topic == topic
    assert vocabulary.tags == []
