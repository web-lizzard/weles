from datetime import UTC, datetime

from pydantic import BaseModel

from domain.capture.exceptions import (
    CaptureSessionClosedError,
    SessionNoteAlreadyDraftedError,
    SessionNoteMissingError,
    SessionTopicAlreadyAssignedError,
)
from domain.capture.note import Note
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import (
    NoteContent,
    NoteId,
    SessionId,
    SessionStatus,
    SessionTopic,
)


class CaptureSession(BaseModel):
    id: SessionId
    topic: SessionTopic | None
    note_id: NoteId | None = None
    status: SessionStatus
    created_at: datetime

    @classmethod
    def start(cls) -> "CaptureSession":
        return cls(
            id=SessionId.new(),
            topic=None,
            note_id=None,
            status=SessionStatus.OPEN,
            created_at=datetime.now(UTC),
        )

    def assign_topic(self, topic: SessionTopic) -> None:
        if self.topic is not None:
            raise SessionTopicAlreadyAssignedError
        self.topic = topic

    def draft_note(
        self,
        topic: Topic,
        content: NoteContent,
        tags: list[Tag],
    ) -> Note:
        if self.status != SessionStatus.OPEN:
            raise CaptureSessionClosedError
        if self.note_id is not None:
            raise SessionNoteAlreadyDraftedError
        note = Note.draft(self.id, topic, content, tags)
        self.note_id = note.id
        return note

    def approve(self, note: Note) -> None:
        if self.status != SessionStatus.OPEN:
            raise CaptureSessionClosedError
        if self.note_id is None or self.note_id != note.id:
            raise SessionNoteMissingError
        note.approve(self.id)
        self._close()

    def _close(self) -> None:
        if self.status != SessionStatus.OPEN:
            raise CaptureSessionClosedError
        self.status = SessionStatus.CLOSED
