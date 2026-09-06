from datetime import UTC, datetime

from pydantic import BaseModel, Field

from domain.distill.exceptions import InvalidDistillationTransitionError
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
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def mark_ready(self) -> None:
        self._ensure_generating()
        self.distillation_status = DistillationStatus.READY

    def mark_failed(self) -> None:
        self._ensure_generating()
        self.distillation_status = DistillationStatus.FAILED

    def _ensure_generating(self) -> None:
        if self.distillation_status is not DistillationStatus.GENERATING:
            raise InvalidDistillationTransitionError

    def _touch(self, at: datetime) -> None:
        self.updated_at = at


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
