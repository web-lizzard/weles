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

    def update_content(self, content: NoteContent) -> None:
        del content
        ...

    def change_topic(self, topic: Topic) -> None:
        del topic
        ...

    def add_tag(self, tag: Tag) -> None:
        del tag
        ...

    def remove_tag(self, tag: Tag) -> None:
        del tag
        ...

    def approve(self, session_id: SessionId) -> None:
        del session_id
        ...
