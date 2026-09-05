from typing import cast

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
from adapters.out.in_memory.distill.card_generation import (
    DeterministicCardGenerationAdapter,
)
from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.note_document_parser import (
    MarkdownNoteDocumentParser,
)
from adapters.out.in_memory.distill.note_repository import (
    InMemoryNoteRepository as InMemoryDistillNoteRepository,
)
from adapters.out.in_memory.distill.unit_of_work import (
    InMemoryUnitOfWork as InMemoryDistillUnitOfWork,
)
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.claimer import InMemoryOutboxClaimer
from adapters.out.in_memory.shared.outbox.envelope_query import (
    InMemoryOutboxEnvelopeQueryAdapter,
)
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from adapters.out.worker.handlers.flashcard_gen import FlashcardGenHandler
from adapters.out.worker.handlers.note_save import SaveNoteHandler
from adapters.out.worker.outbox_worker import OutboxWorker
from application.capture.commands.approve_note import ApproveNoteCommand
from application.capture.commands.send_message import GenerateReplyCommand
from application.capture.commands.start_capture_session import (
    StartCaptureSessionCommand,
)
from application.capture.ports import UnitOfWork
from application.capture.services.vocabulary import VocabularyResolver
from application.distill.commands.generate_cards import GenerateCardsCommand
from application.distill.commands.save_note import SaveNoteCommand
from application.distill.ports import UnitOfWork as DistillUnitOfWork
from application.shared.outbox.queries.envelopes import OutboxEnvelopeQueryPort
from config.settings import Settings
from domain.capture.ports import CaptureSessionRepository
from domain.capture.value_objects import SimilarityScore
from domain.capture.vocabulary import MatchCriteria
from domain.distill.card_factory import CardFactory
from domain.distill.value_objects import CardLengthPolicy

_settings = Settings()  # pyright: ignore[reportCallIssue]
_store = InMemoryMessageStore()
_capture_session_repository = InMemoryCaptureSessionRepository()
_message_repository = InMemoryMessageRepository(_store)
_note_repository = InMemoryNoteRepository()
_topic_repository = InMemoryTopicRepository()
_tag_repository = InMemoryTagRepository()
_note_vocabulary = InMemoryNoteVocabularyRepository(_topic_repository, _tag_repository)
_outbox_store = InMemoryOutboxStore()
_outbox_appender = InMemoryOutboxAppender(_outbox_store)
_outbox_claimer = InMemoryOutboxClaimer(_outbox_store)
_outbox_query = InMemoryOutboxEnvelopeQueryAdapter(_outbox_store)
_distill_note_repository = InMemoryDistillNoteRepository()
_distill_card_repository = InMemoryCardRepository()
_note_document_parser = MarkdownNoteDocumentParser()
_card_generation = DeterministicCardGenerationAdapter()
_card_factory = CardFactory(
    CardLengthPolicy(
        front_max=_settings.card_front_max, back_max=_settings.card_back_max
    )
)
_transcript_query = InMemoryTranscriptQueryAdapter(_store)
_topic_extraction = DeterministicTopicExtractionAdapter()
_confidence_assessment = DeterministicConfidenceAssessmentAdapter()
_reply_generation = DeterministicReplyGenerationAdapter()
_embedding = DeterministicEmbeddingAdapter()
_vocabulary = VocabularyResolver(
    _embedding,
    MatchCriteria(
        threshold=SimilarityScore(value=_settings.vocabulary_match_threshold)
    ),
)


def _unit_of_work() -> UnitOfWork:
    return cast(
        UnitOfWork,
        cast(
            object,
            InMemoryUnitOfWork(
                _capture_session_repository,
                _message_repository,
                _store,
                _note_repository,
                _topic_repository,
                _tag_repository,
                _note_vocabulary,
                _outbox_store,
                _outbox_appender,
            ),
        ),
    )


def _distill_unit_of_work() -> DistillUnitOfWork:
    return cast(
        DistillUnitOfWork,
        cast(
            object,
            InMemoryDistillUnitOfWork(
                _distill_note_repository,
                _distill_card_repository,
                _outbox_store,
                _outbox_appender,
            ),
        ),
    )


_save_note_command = SaveNoteCommand(uow_factory=_distill_unit_of_work)
_save_note_handler = SaveNoteHandler(_save_note_command)
_generate_cards_command = GenerateCardsCommand(
    uow_factory=_distill_unit_of_work,
    card_generation=_card_generation,
    parser=_note_document_parser,
    card_factory=_card_factory,
)
_flashcard_gen_handler = FlashcardGenHandler(_generate_cards_command)
_outbox_worker = OutboxWorker(
    _outbox_claimer,
    [_save_note_handler, _flashcard_gen_handler],
    worker_id=_settings.outbox_worker_id,
    batch_size=_settings.outbox_batch_size,
    max_attempts=_settings.outbox_max_attempts,
)


def get_capture_session_repository() -> CaptureSessionRepository:
    return _capture_session_repository


def get_start_capture_session_command() -> StartCaptureSessionCommand:
    return StartCaptureSessionCommand(uow=_unit_of_work())


def get_generate_reply_command() -> GenerateReplyCommand:
    return GenerateReplyCommand(
        capture_sessions=_capture_session_repository,
        uow=_unit_of_work(),
        transcript_query=_transcript_query,
        topic_extraction=_topic_extraction,
        confidence_assessment=_confidence_assessment,
        reply_generation=_reply_generation,
        vocabulary=_vocabulary,
    )


def get_approve_note_command() -> ApproveNoteCommand:
    return ApproveNoteCommand(uow=_unit_of_work())


def get_outbox_envelope_query() -> OutboxEnvelopeQueryPort:
    return _outbox_query


def get_outbox_worker() -> OutboxWorker:
    return _outbox_worker
