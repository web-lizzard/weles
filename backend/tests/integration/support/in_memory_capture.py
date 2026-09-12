from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from adapters.compose import (
    get_approve_note_command,
    get_capture_session_repository,
    get_generate_reply_command,
    get_outbox_envelope_query,
    get_start_capture_session_command,
)
from adapters.out.in_memory.capture.capture_agent import (
    DeterministicCaptureAgentAdapter,
)
from adapters.out.in_memory.capture.capture_session_repository import (
    InMemoryCaptureSessionRepository,
)
from adapters.out.in_memory.capture.confidence_assessment import (
    DeterministicConfidenceAssessmentAdapter,
)
from adapters.out.in_memory.capture.embedding import DeterministicEmbeddingAdapter
from adapters.out.in_memory.capture.message_repository import (
    InMemoryMessageRepository,
)
from adapters.out.in_memory.capture.message_store import InMemoryMessageStore
from adapters.out.in_memory.capture.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.capture.note_vocabulary_repository import (
    InMemoryNoteVocabularyRepository,
)
from adapters.out.in_memory.capture.reply_generation import (
    DeterministicReplyGenerationAdapter,
)
from adapters.out.in_memory.capture.tag_repository import InMemoryTagRepository
from adapters.out.in_memory.capture.topic_extraction import (
    DeterministicTopicExtractionAdapter,
)
from adapters.out.in_memory.capture.topic_repository import InMemoryTopicRepository
from adapters.out.in_memory.capture.transcript_query import (
    InMemoryTranscriptQueryAdapter,
)
from adapters.out.in_memory.capture.unit_of_work import InMemoryUnitOfWork
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.envelope_query import (
    InMemoryOutboxEnvelopeQueryAdapter,
)
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from application.capture.commands.approve_note import ApproveNoteCommand
from application.capture.commands.send_message import GenerateReplyCommand
from application.capture.commands.start_capture_session import (
    StartCaptureSessionCommand,
)
from application.capture.ports import ConfidenceAssessmentPort, UnitOfWork
from application.capture.services.vocabulary import VocabularyResolver
from application.shared.outbox.queries.envelopes import OutboxEnvelopeQueryPort
from domain.capture.value_objects import SimilarityScore
from domain.capture.vocabulary import MatchCriteria


@dataclass
class InMemoryCaptureComposition:
    store: InMemoryMessageStore
    capture_sessions: InMemoryCaptureSessionRepository
    messages: InMemoryMessageRepository
    notes: InMemoryNoteRepository
    topics: InMemoryTopicRepository
    tags: InMemoryTagRepository
    outbox_store: InMemoryOutboxStore
    outbox: InMemoryOutboxAppender
    outbox_query: InMemoryOutboxEnvelopeQueryAdapter
    transcript_query: InMemoryTranscriptQueryAdapter
    topic_extraction: DeterministicTopicExtractionAdapter
    confidence_assessment: ConfidenceAssessmentPort
    reply_generation: DeterministicReplyGenerationAdapter
    capture_agent: DeterministicCaptureAgentAdapter
    embedding: DeterministicEmbeddingAdapter
    vocabulary: VocabularyResolver

    @classmethod
    def create(cls) -> "InMemoryCaptureComposition":
        store = InMemoryMessageStore()
        capture_sessions = InMemoryCaptureSessionRepository()
        messages = InMemoryMessageRepository(store)
        notes = InMemoryNoteRepository()
        topics = InMemoryTopicRepository()
        tags = InMemoryTagRepository()
        outbox_store = InMemoryOutboxStore()
        outbox = InMemoryOutboxAppender(outbox_store)
        outbox_query = InMemoryOutboxEnvelopeQueryAdapter(outbox_store)
        embedding = DeterministicEmbeddingAdapter()
        return cls(
            store=store,
            capture_sessions=capture_sessions,
            messages=messages,
            notes=notes,
            topics=topics,
            tags=tags,
            outbox_store=outbox_store,
            outbox=outbox,
            outbox_query=outbox_query,
            transcript_query=InMemoryTranscriptQueryAdapter(store),
            topic_extraction=DeterministicTopicExtractionAdapter(),
            confidence_assessment=DeterministicConfidenceAssessmentAdapter(),
            reply_generation=DeterministicReplyGenerationAdapter(),
            capture_agent=DeterministicCaptureAgentAdapter(),
            embedding=embedding,
            vocabulary=VocabularyResolver(
                embedding, MatchCriteria(threshold=SimilarityScore(value=0.85))
            ),
        )

    def unit_of_work(self) -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(
            self.capture_sessions,
            self.messages,
            self.store,
            self.notes,
            self.topics,
            self.tags,
            InMemoryNoteVocabularyRepository(self.topics, self.tags),
            self.outbox_store,
            self.outbox,
        )

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
                capture_sessions=composition.capture_sessions,
                uow=cast(UnitOfWork, cast(object, composition.unit_of_work())),
                capture_agent=composition.capture_agent,
                vocabulary=composition.vocabulary,
            )

        def override_approve_note_command() -> ApproveNoteCommand:
            return ApproveNoteCommand(
                uow=cast(UnitOfWork, cast(object, composition.unit_of_work()))
            )

        def override_outbox_envelope_query() -> OutboxEnvelopeQueryPort:
            return composition.outbox_query

        return {
            get_capture_session_repository: override_capture_session_repository,
            get_start_capture_session_command: override_start_capture_session_command,
            get_generate_reply_command: override_generate_reply_command,
            get_approve_note_command: override_approve_note_command,
            get_outbox_envelope_query: override_outbox_envelope_query,
        }
