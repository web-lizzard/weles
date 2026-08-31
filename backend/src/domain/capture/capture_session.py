from datetime import UTC, datetime

from pydantic import BaseModel

from domain.capture.exceptions import SessionTopicAlreadyAssignedError
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
        _topic: Topic,
        _content: NoteContent,
        _tags: list[Tag],
    ) -> Note:
        raise NotImplementedError
