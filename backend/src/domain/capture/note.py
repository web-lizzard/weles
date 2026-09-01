from datetime import UTC, datetime

from pydantic import BaseModel

from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import (
    NoteContent,
    NoteId,
    NoteStatus,
    SessionId,
    TagId,
    TopicId,
)


class Note(BaseModel):
    id: NoteId
    session_id: SessionId
    topic_id: TopicId
    content: NoteContent
    tag_ids: list[TagId]
    status: NoteStatus
    created_at: datetime
    approved_at: datetime | None

    @classmethod
    def draft(
        cls,
        session_id: SessionId,
        topic: Topic,
        content: NoteContent,
        tags: list[Tag],
    ) -> "Note":
        return cls(
            id=NoteId.new(),
            session_id=session_id,
            topic_id=topic.id,
            content=content,
            tag_ids=[tag.id for tag in tags],
            status=NoteStatus.DRAFT,
            created_at=datetime.now(UTC),
            approved_at=None,
        )
