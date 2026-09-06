from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

from domain.distill.card import Card
from domain.distill.note import Note
from domain.distill.value_objects import (
    Anchor,
    CardId,
    CardSide,
    DistillationStatus,
    NoteContent,
    NoteId,
    SessionId,
    TagSnapshot,
    TopicSnapshot,
)

from .conftest import NotesTestContext


def _note(status: DistillationStatus, updated_at: datetime) -> Note:
    return Note(
        id=NoteId(value=uuid4()),
        session_id=SessionId(value=uuid4()),
        topic=TopicSnapshot(id=uuid4(), label="TCP handshakes"),
        content=NoteContent(value="We discussed how connections are established."),
        tags=[TagSnapshot(id=uuid4(), label="networking")],
        distillation_status=status,
        approved_at=updated_at,
        created_at=updated_at,
        updated_at=updated_at,
    )


def _card(note_id: NoteId, created_at: datetime) -> Card:
    return Card(
        id=CardId(value=uuid4()),
        note_id=note_id,
        front=CardSide(value="What establishes a connection?"),
        back=CardSide(value="A three-way handshake."),
        anchor=Anchor(quote="Connections are established via a three-way handshake."),
        discard=None,
        created_at=created_at,
    )


async def test_get_notes_returns_seeded_notes_shaped_and_ordered_by_recency(
    notes_client: NotesTestContext,
) -> None:
    now = datetime.now(UTC)
    older = _note(DistillationStatus.READY, now)
    newer = _note(DistillationStatus.GENERATING, now + timedelta(minutes=5))
    await notes_client.notes.save(older)
    await notes_client.notes.save(newer)
    await notes_client.cards.save(_card(older.id, now))

    response = notes_client.client.get("/notes")

    assert response.status_code == 200
    body = cast(list[dict[str, object]], response.json())
    assert [item["note_id"] for item in body] == [
        str(newer.id.value),
        str(older.id.value),
    ]
    assert body[1]["topic_label"] == older.topic.label
    assert body[1]["distillation_status"] == "ready"
    assert body[1]["card_count"] == 1


async def test_get_notes_returns_empty_list_when_no_notes_saved(
    notes_client: NotesTestContext,
) -> None:
    response = notes_client.client.get("/notes")

    assert response.status_code == 200
    assert response.json() == []


async def test_get_note_returns_seeded_note_shaped_for_a_known_id(
    notes_client: NotesTestContext,
) -> None:
    now = datetime.now(UTC)
    note = _note(DistillationStatus.READY, now)
    await notes_client.notes.save(note)

    response = notes_client.client.get(f"/notes/{note.id.value}")

    assert response.status_code == 200
    body = cast(dict[str, object], response.json())
    assert body["note_id"] == str(note.id.value)
    assert body["topic"] == {"id": str(note.topic.id), "label": note.topic.label}
    assert body["content"] == note.content.value
    assert body["tags"] == [
        {"id": str(tag.id), "label": tag.label} for tag in note.tags
    ]
    assert body["distillation_status"] == "ready"


async def test_get_note_returns_404_for_an_unknown_note_id(
    notes_client: NotesTestContext,
) -> None:
    response = notes_client.client.get(f"/notes/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["code"] == "distill_note_not_found"
