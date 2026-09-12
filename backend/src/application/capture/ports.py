from typing import Protocol

from domain.capture.ports import (
    CaptureSessionRepository,
    MessageRepository,
    NoteRepository,
    NoteVocabularyRepository,
    TagRepository,
    TopicRepository,
)
from domain.shared.outbox.ports import OutboxAppender


class UnitOfWork(Protocol):
    capture_sessions: CaptureSessionRepository
    messages: MessageRepository
    notes: NoteRepository
    topics: TopicRepository
    tags: TagRepository
    note_vocabulary: NoteVocabularyRepository
    outbox: OutboxAppender

    async def __aenter__(self) -> "UnitOfWork": ...

    async def __aexit__(self, *exc: object) -> None: ...

    async def commit(self) -> None: ...
