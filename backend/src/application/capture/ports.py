from collections.abc import AsyncIterator
from typing import Protocol

from application.capture.value_objects import (
    ConfidenceAssessment,
    ReplyChunk,
    Transcript,
)
from domain.capture.ports import (
    CaptureSessionRepository,
    MessageRepository,
    NoteRepository,
    NoteVocabularyRepository,
    TagRepository,
    TopicRepository,
)
from domain.capture.value_objects import Embedding, MessageContent, SessionTopic
from domain.shared.outbox.ports import OutboxAppender


class TopicExtractionPort(Protocol):
    async def extract(self, first_message: MessageContent) -> SessionTopic: ...


class ConfidenceAssessmentPort(Protocol):
    async def assess(self, transcript: Transcript) -> ConfidenceAssessment: ...


class ReplyGenerationPort(Protocol):
    def generate(
        self, transcript: Transcript, assessment: ConfidenceAssessment
    ) -> AsyncIterator[ReplyChunk]: ...


class EmbeddingPort(Protocol):
    async def embed(self, text: str) -> Embedding: ...


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
