from datetime import UTC, datetime

from domain.capture.note import Note
from domain.capture.outbox import NOTE_APPROVED, NoteApprovedPayload, VocabularySnapshot
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import (
    Embedding,
    Label,
    NoteContent,
    NoteId,
    NoteStatus,
    SessionId,
)
from domain.shared.outbox.model import EnvelopeStatus


def _approved_note(session_id: SessionId, topic: Topic, tags: list[Tag]) -> Note:
    return Note(
        id=NoteId.new(),
        session_id=session_id,
        topic_id=topic.id,
        content=NoteContent(value="We discussed how connections are established."),
        tag_ids=[tag.id for tag in tags],
        status=NoteStatus.APPROVED,
        created_at=datetime.now(UTC),
        approved_at=datetime.now(UTC),
    )


def test_of_snapshots_labels_and_to_envelope_builds_a_pending_envelope() -> None:
    session_id = SessionId.new()
    topic = Topic.mint(Label(value="TCP handshakes"), Embedding(values=(0.1, 0.2)))
    tag = Tag.mint(Label(value="networking"), Embedding(values=(0.3, 0.4)))
    note = _approved_note(session_id, topic, [tag])

    payload = NoteApprovedPayload.of(note, topic, [tag])

    assert payload.note_id == note.id.value
    assert payload.session_id == session_id.value
    assert payload.content == note.content.value
    assert payload.approved_at == note.approved_at
    assert payload.topic == VocabularySnapshot(
        id=topic.id.value, label=topic.label.value
    )
    assert payload.tags == [VocabularySnapshot(id=tag.id.value, label=tag.label.value)]

    envelope = payload.to_envelope()

    assert envelope.type == NOTE_APPROVED
    assert envelope.status == EnvelopeStatus.PENDING
    assert envelope.payload["note_id"] == str(note.id.value)
