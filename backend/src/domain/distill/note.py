from datetime import UTC, datetime

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

    def mark_ready(self) -> None: ...

    def mark_failed(self) -> None: ...

    def _ensure_generating(self) -> None: ...


def mint_note(
    note_id: NoteId,
    session_id: SessionId,
    topic: TopicSnapshot,
    content: NoteContent,
    tags: list[TagSnapshot],
    approved_at: datetime,
) -> Note:
    return Note(
        id=note_id,
        session_id=session_id,
        topic=topic,
        content=content,
        tags=tags,
        distillation_status=DistillationStatus.GENERATING,
        approved_at=approved_at,
        created_at=datetime.now(UTC),
    )
