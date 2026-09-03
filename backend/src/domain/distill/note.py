from datetime import datetime

from pydantic import BaseModel

from domain.distill.value_objects import (
    DistillationStatus,
    NoteContent,
    NoteId,
    SessionId,
    TagSnapshot,
    TopicSnapshot,
)


class Note(BaseModel):
    id: NoteId
    session_id: SessionId
    topic: TopicSnapshot
    content: NoteContent
    tags: list[TagSnapshot]
    distillation_status: DistillationStatus
    approved_at: datetime
    created_at: datetime


def mint_note(
    _note_id: NoteId,
    _session_id: SessionId,
    _topic: TopicSnapshot,
    _content: NoteContent,
    _tags: list[TagSnapshot],
    _approved_at: datetime,
) -> Note: ...
