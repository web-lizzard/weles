from collections.abc import AsyncIterator
from typing import Protocol

from application.capture.value_objects import ConfidenceAssessment, Transcript
from domain.capture.ports import CaptureSessionRepository, MessageRepository
from domain.capture.value_objects import MessageContent, SessionTopic


class TopicExtractionPort(Protocol):
    async def extract(self, first_message: MessageContent) -> SessionTopic: ...


class ConfidenceAssessmentPort(Protocol):
    async def assess(self, transcript: Transcript) -> ConfidenceAssessment: ...


class ReplyGenerationPort(Protocol):
    def generate(
        self, transcript: Transcript, assessment: ConfidenceAssessment
    ) -> AsyncIterator[str]: ...


class UnitOfWork(Protocol):
    capture_sessions: CaptureSessionRepository
    messages: MessageRepository

    async def __aenter__(self) -> "UnitOfWork": ...

    async def __aexit__(self, *exc: object) -> None: ...

    async def commit(self) -> None: ...
