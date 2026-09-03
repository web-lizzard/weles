from datetime import UTC, datetime
from uuid import uuid4

from domain.distill.note import mint_note
from domain.distill.value_objects import (
    DistillationStatus,
    NoteContent,
    NoteId,
    SessionId,
    TagSnapshot,
    TopicSnapshot,
)


def test_mint_note_maps_every_field_and_starts_generating() -> None:
    note_id = NoteId(value=uuid4())
    session_id = SessionId(value=uuid4())
    topic = TopicSnapshot(id=uuid4(), label="TCP handshakes")
    content = NoteContent(value="We discussed how connections are established.")
    tags = [TagSnapshot(id=uuid4(), label="networking")]
    approved_at = datetime.now(UTC)

    note = mint_note(note_id, session_id, topic, content, tags, approved_at)

    assert note.id == note_id
    assert note.session_id == session_id
    assert note.topic == topic
    assert note.content == content
    assert note.tags == tags
    assert note.distillation_status == DistillationStatus.GENERATING
    assert note.approved_at == approved_at


def test_mint_note_stamps_created_at_in_utc_near_now() -> None:
    before = datetime.now(UTC)

    note = mint_note(
        NoteId(value=uuid4()),
        SessionId(value=uuid4()),
        TopicSnapshot(id=uuid4(), label="TCP handshakes"),
        NoteContent(value="We discussed how connections are established."),
        [],
        before,
    )

    after = datetime.now(UTC)

    assert note.created_at.tzinfo is UTC
    assert before <= note.created_at <= after
