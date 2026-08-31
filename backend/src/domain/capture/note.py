from datetime import datetime

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
        _session_id: SessionId,
        _topic: Topic,
        _content: NoteContent,
        _tags: list[Tag],
    ) -> "Note":
        raise NotImplementedError
