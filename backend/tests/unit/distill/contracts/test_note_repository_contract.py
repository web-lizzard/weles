from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import pytest

from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from domain.distill.note import Note
from domain.distill.ports import NoteRepository
from domain.distill.value_objects import (
    DistillationStatus,
    NoteContent,
    NoteId,
    SessionId,
    TagSnapshot,
    TopicSnapshot,
)

_IMPLEMENTATIONS: list[Callable[[], NoteRepository]] = [
    cast(Callable[[], NoteRepository], InMemoryNoteRepository),
]


def _sample_note() -> Note:
    return Note(
        id=NoteId(value=uuid4()),
        session_id=SessionId(value=uuid4()),
        topic=TopicSnapshot(id=uuid4(), label="TCP handshakes"),
        content=NoteContent(value="We discussed how connections are established."),
        tags=[TagSnapshot(id=uuid4(), label="networking")],
        distillation_status=DistillationStatus.GENERATING,
        approved_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_add_then_get_returns_the_saved_note(
    make_repository: Callable[[], NoteRepository],
) -> None:
    repository = make_repository()
    note = _sample_note()

    await repository.save(note)
    result = await repository.get(note.id)

    assert result == note


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_get_returns_none_for_unknown_note_id(
    make_repository: Callable[[], NoteRepository],
) -> None:
    repository = make_repository()

    result = await repository.get(NoteId(value=uuid4()))

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

    await repository.save(original)
    await repository.save(updated)
    result = await repository.get(original.id)

    assert result == updated
