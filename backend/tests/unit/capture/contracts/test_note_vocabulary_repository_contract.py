from collections.abc import Callable
from dataclasses import dataclass

import pytest

from adapters.out.in_memory.capture.note_vocabulary_repository import (
    InMemoryNoteVocabularyRepository,
)
from adapters.out.in_memory.capture.tag_repository import InMemoryTagRepository
from adapters.out.in_memory.capture.topic_repository import InMemoryTopicRepository
from domain.capture.exceptions import NoteVocabularyIncompleteError
from domain.capture.note import Note
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import (
    Embedding,
    Label,
    NoteContent,
    SessionId,
    TagId,
)


@dataclass
class _VocabularyFixture:
    topics: InMemoryTopicRepository
    tags: InMemoryTagRepository
    repository: InMemoryNoteVocabularyRepository


def _make_fixture() -> _VocabularyFixture:
    topics = InMemoryTopicRepository()
    tags = InMemoryTagRepository()
    return _VocabularyFixture(
        topics=topics,
        tags=tags,
        repository=InMemoryNoteVocabularyRepository(topics, tags),
    )


_IMPLEMENTATIONS: list[Callable[[], _VocabularyFixture]] = [_make_fixture]


def _sample_topic() -> Topic:
    return Topic.mint(
        Label(value="TCP handshakes"),
        Embedding(values=(0.1, 0.2)),
    )


def _sample_tag() -> Tag:
    return Tag.mint(
        Label(value="networking"),
        Embedding(values=(0.3, 0.4)),
    )


def _note_for(topic: Topic, tags: list[Tag]) -> Note:
    return Note.draft(
        session_id=SessionId.new(),
        topic=topic,
        content=NoteContent(value="We discussed how connections are established."),
        tags=tags,
    )


@pytest.mark.parametrize("make_fixture", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_resolve_returns_topic_and_tags_when_all_references_exist(
    make_fixture: Callable[[], _VocabularyFixture],
) -> None:
    fixture = make_fixture()
    topic = _sample_topic()
    tag = _sample_tag()
    note = _note_for(topic, [tag])
    await fixture.topics.add(topic)
    await fixture.tags.add(tag)

    vocabulary = await fixture.repository.resolve(note)

    assert vocabulary.topic == topic
    assert vocabulary.tags == [tag]


@pytest.mark.parametrize("make_fixture", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_resolve_raises_when_topic_is_missing(
    make_fixture: Callable[[], _VocabularyFixture],
) -> None:
    fixture = make_fixture()
    topic = _sample_topic()
    tag = _sample_tag()
    note = _note_for(topic, [tag])
    await fixture.tags.add(tag)

    with pytest.raises(NoteVocabularyIncompleteError):
        _ = await fixture.repository.resolve(note)


@pytest.mark.parametrize("make_fixture", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_resolve_raises_when_a_tag_is_missing(
    make_fixture: Callable[[], _VocabularyFixture],
) -> None:
    fixture = make_fixture()
    topic = _sample_topic()
    present_tag = _sample_tag()
    missing_tag_id = TagId.new()
    note = _note_for(topic, [present_tag]).model_copy(
        update={"tag_ids": [present_tag.id, missing_tag_id]}
    )
    await fixture.topics.add(topic)
    await fixture.tags.add(present_tag)

    with pytest.raises(NoteVocabularyIncompleteError):
        _ = await fixture.repository.resolve(note)


@pytest.mark.parametrize("make_fixture", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_resolve_returns_empty_tags_when_note_has_no_tag_ids(
    make_fixture: Callable[[], _VocabularyFixture],
) -> None:
    fixture = make_fixture()
    topic = _sample_topic()
    note = _note_for(topic, [])
    await fixture.topics.add(topic)

    vocabulary = await fixture.repository.resolve(note)

    assert vocabulary.topic == topic
    assert vocabulary.tags == []
