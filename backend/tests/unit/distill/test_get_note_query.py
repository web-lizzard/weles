from datetime import UTC, datetime
from uuid import uuid4

import pytest

from adapters.out.in_memory.distill.get_note_query import InMemoryGetNoteQueryAdapter
from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from domain.distill.exceptions import DistillNoteNotFoundError
from domain.distill.note import Note
from domain.distill.value_objects import (
    DistillationStatus,
    NoteContent,
    NoteId,
    SessionId,
    TagSnapshot,
    TopicSnapshot,
)


def _note(status: DistillationStatus, at: datetime) -> Note:
    return Note(
        id=NoteId(value=uuid4()),
        session_id=SessionId(value=uuid4()),
        topic=TopicSnapshot(id=uuid4(), label="TCP handshakes"),
        content=NoteContent(value="We discussed how connections are established."),
        tags=[TagSnapshot(id=uuid4(), label="networking")],
        distillation_status=status,
        approved_at=at,
        created_at=at,
        updated_at=at,
    )


async def test_get_note_maps_full_note_shape_into_the_detail_dto() -> None:
    note_repository = InMemoryNoteRepository()
    now = datetime.now(UTC)
    note = _note(DistillationStatus.READY, now)
    await note_repository.save(note)
    query = InMemoryGetNoteQueryAdapter(note_repository)

    result = await query.get_note(note.id)

    assert result.note_id == note.id.value
    assert result.topic.id == note.topic.id
    assert result.topic.label == note.topic.label
    assert result.content == note.content.value
    assert [(tag.id, tag.label) for tag in result.tags] == [
        (t.id, t.label) for t in note.tags
    ]
    assert result.distillation_status == "ready"
    assert result.approved_at == note.approved_at
    assert result.created_at == note.created_at
    assert result.updated_at == note.updated_at


async def test_get_note_raises_not_found_for_an_unknown_note_id() -> None:
    query = InMemoryGetNoteQueryAdapter(InMemoryNoteRepository())

    with pytest.raises(DistillNoteNotFoundError):
        _ = await query.get_note(NoteId(value=uuid4()))


@pytest.mark.parametrize(
    "status",
    [
        DistillationStatus.GENERATING,
        DistillationStatus.READY,
        DistillationStatus.FAILED,
    ],
)
async def test_get_note_exposes_raw_distillation_status(
    status: DistillationStatus,
) -> None:
    note_repository = InMemoryNoteRepository()
    note = _note(status, datetime.now(UTC))
    await note_repository.save(note)
    query = InMemoryGetNoteQueryAdapter(note_repository)

    result = await query.get_note(note.id)

    assert result.distillation_status == status.value
