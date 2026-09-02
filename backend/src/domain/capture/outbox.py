from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from domain.capture.note import Note
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.shared.outbox.model import OutboxEnvelope

NOTE_APPROVED = "note_approved"


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
    def of(cls, _note: Note, _topic: Topic, _tags: list[Tag]) -> "NoteApprovedPayload":
        raise NotImplementedError

    def to_envelope(self) -> OutboxEnvelope:
        raise NotImplementedError
