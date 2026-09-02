from datetime import UTC, datetime

from pydantic import BaseModel

from domain.capture.exceptions import (
    NoteNotDraftError,
    NoteSessionMismatchError,
    TagNotOnNoteError,
)
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
        self._ensure_draft()
        self.content = content

    def change_topic(self, topic: Topic) -> None:
        self._ensure_draft()
        self.topic_id = topic.id

    def add_tag(self, tag: Tag) -> None:
        self._ensure_draft()
        if tag.id not in self.tag_ids:
            self.tag_ids.append(tag.id)

    def remove_tag(self, tag: Tag) -> None:
        self._ensure_draft()
        if tag.id not in self.tag_ids:
            raise TagNotOnNoteError
        self.tag_ids.remove(tag.id)

    def approve(self, session_id: SessionId) -> None:
        if session_id != self.session_id:
            raise NoteSessionMismatchError
        self._ensure_draft()
        self.status = NoteStatus.APPROVED
        self.approved_at = datetime.now(UTC)

    def _ensure_draft(self) -> None:
        if self.status != NoteStatus.DRAFT:
            raise NoteNotDraftError
