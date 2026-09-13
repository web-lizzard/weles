from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast

import pytest

from adapters.out.in_memory.capture.note_repository import InMemoryNoteRepository
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

_IMPLEMENTATIONS: list[Callable[[], NoteRepository]] = [
    cast(Callable[[], NoteRepository], InMemoryNoteRepository),
]

_EMBEDDING_MODEL = "test"


def _sample_note() -> Note:
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
    return Note(
        id=NoteId.new(),
        session_id=SessionId.new(),
        topic_id=topic.id,
        content=NoteContent(value="We discussed how connections are established."),
        tag_ids=[tag.id],
        status=NoteStatus.DRAFT,
        created_at=datetime.now(UTC),
        approved_at=None,
    )


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_add_then_get_returns_the_saved_note(
    make_repository: Callable[[], NoteRepository],
) -> None:
    repository = make_repository()
    note = _sample_note()

    await repository.add(note)
    result = await repository.get(note.id)

    assert result == note


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_get_returns_none_for_unknown_note_id(
    make_repository: Callable[[], NoteRepository],
) -> None:
    repository = make_repository()

    result = await repository.get(NoteId.new())

    assert result is None


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_second_add_with_same_id_overwrites(
    make_repository: Callable[[], NoteRepository],
) -> None:
    repository = make_repository()
    original = _sample_note()
    updated = original.model_copy(
        update={"content": NoteContent(value="Updated body text.")}
    )

    await repository.add(original)
    await repository.add(updated)
    result = await repository.get(original.id)

    assert result == updated
