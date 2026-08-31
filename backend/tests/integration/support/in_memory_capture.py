from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from adapters.compose import (
    get_capture_session_repository,
    get_generate_reply_command,
    get_start_capture_session_command,
)
from adapters.out.in_memory.capture.capture_session_repository import (
    InMemoryCaptureSessionRepository,
)
from adapters.out.in_memory.capture.confidence_assessment import (
    DeterministicConfidenceAssessmentAdapter,
)
from adapters.out.in_memory.capture.message_repository import (
    InMemoryMessageRepository,
)
from adapters.out.in_memory.capture.message_store import InMemoryMessageStore
from adapters.out.in_memory.capture.reply_generation import (
    DeterministicReplyGenerationAdapter,
)
from adapters.out.in_memory.capture.topic_extraction import (
    DeterministicTopicExtractionAdapter,
)
from adapters.out.in_memory.capture.transcript_query import (
    InMemoryTranscriptQueryAdapter,
)
from adapters.out.in_memory.capture.unit_of_work import InMemoryUnitOfWork
from application.capture.commands.send_message import GenerateReplyCommand
from application.capture.commands.start_capture_session import (
    StartCaptureSessionCommand,
)
from application.capture.ports import UnitOfWork


@dataclass
class InMemoryCaptureComposition:
    store: InMemoryMessageStore
    capture_sessions: InMemoryCaptureSessionRepository
    messages: InMemoryMessageRepository
    transcript_query: InMemoryTranscriptQueryAdapter
    topic_extraction: DeterministicTopicExtractionAdapter
    confidence_assessment: DeterministicConfidenceAssessmentAdapter
    reply_generation: DeterministicReplyGenerationAdapter

    @classmethod
    def create(cls) -> "InMemoryCaptureComposition":
        store = InMemoryMessageStore()
        capture_sessions = InMemoryCaptureSessionRepository()
        messages = InMemoryMessageRepository(store)
        return cls(
            store=store,
            capture_sessions=capture_sessions,
            messages=messages,
            transcript_query=InMemoryTranscriptQueryAdapter(store),
            topic_extraction=DeterministicTopicExtractionAdapter(),
            confidence_assessment=DeterministicConfidenceAssessmentAdapter(),
            reply_generation=DeterministicReplyGenerationAdapter(),
        )

    def unit_of_work(self) -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(self.capture_sessions, self.messages, self.store)

    def dependency_overrides(
        self,
    ) -> dict[Callable[..., object], Callable[..., object]]:
        composition = self

        def override_capture_session_repository() -> InMemoryCaptureSessionRepository:
            return composition.capture_sessions

        def override_start_capture_session_command() -> StartCaptureSessionCommand:
            return StartCaptureSessionCommand(
                uow=cast(UnitOfWork, cast(object, composition.unit_of_work()))
            )

        def override_generate_reply_command() -> GenerateReplyCommand:
            return GenerateReplyCommand(
                uow=cast(UnitOfWork, cast(object, composition.unit_of_work())),
                transcript_query=composition.transcript_query,
                topic_extraction=composition.topic_extraction,
                confidence_assessment=composition.confidence_assessment,
                reply_generation=composition.reply_generation,
            )

        return {
            get_capture_session_repository: override_capture_session_repository,
            get_start_capture_session_command: override_start_capture_session_command,
            get_generate_reply_command: override_generate_reply_command,
        }
