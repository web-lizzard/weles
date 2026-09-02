from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from domain.capture.note import Note
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.shared.outbox.model import EnvelopeType, OutboxEnvelope

NOTE_APPROVED = EnvelopeType(name="note_approved")


class VocabularySnapshot(BaseModel, frozen=True):
    id: UUID
    label: str


class NoteApprovedPayload(BaseModel, frozen=True):
    note_id: UUID
    session_id: UUID
    topic: VocabularySnapshot
    content: str
    tags: list[VocabularySnapshot]
    approved_at: datetime

    @classmethod
    def of(cls, note: Note, topic: Topic, tags: list[Tag]) -> "NoteApprovedPayload":
        assert note.approved_at is not None
        return cls(
            note_id=note.id.value,
            session_id=note.session_id.value,
            topic=VocabularySnapshot(id=topic.id.value, label=topic.label.value),
            content=note.content.value,
            tags=[
                VocabularySnapshot(id=tag.id.value, label=tag.label.value)
                for tag in tags
            ],
            approved_at=note.approved_at,
        )

    def to_envelope(self) -> OutboxEnvelope:
        return OutboxEnvelope.pending(NOTE_APPROVED, self.model_dump(mode="json"))
