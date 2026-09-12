import asyncio
from datetime import timedelta
from typing import cast

from adapters.out.fsrs.scheduler import FsrsScheduler
from adapters.out.in_memory.capture.capture_agent import (
    DeterministicCaptureAgentAdapter,
)
from adapters.out.in_memory.capture.capture_session_repository import (
    InMemoryCaptureSessionRepository,
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
from adapters.out.in_memory.capture.tag_repository import InMemoryTagRepository
from adapters.out.in_memory.capture.topic_repository import InMemoryTopicRepository
from adapters.out.in_memory.capture.unit_of_work import InMemoryUnitOfWork
from adapters.out.in_memory.distill.card_generation import (
    DeterministicCardGenerationAdapter,
)
from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.get_note_query import (
    InMemoryGetNoteQueryAdapter,
)
from adapters.out.in_memory.distill.list_cards_for_note_query import (
    InMemoryListCardsForNoteQueryAdapter,
)
from adapters.out.in_memory.distill.list_notes_query import (
    InMemoryListNotesQueryAdapter,
)
from adapters.out.in_memory.distill.note_repository import (
    InMemoryNoteRepository as InMemoryDistillNoteRepository,
)
from adapters.out.in_memory.distill.unit_of_work import (
    InMemoryUnitOfWork as InMemoryDistillUnitOfWork,
)
from adapters.out.in_memory.remember.card_source_locator import (
    InMemoryCardSourceLocator,
)
from adapters.out.in_memory.remember.clock import SystemClock
from adapters.out.in_memory.remember.review_catalog import InMemoryReviewCatalog
from adapters.out.in_memory.remember.review_event_store import InMemoryReviewEventStore
from adapters.out.in_memory.remember.scheduling_state_repository import (
    InMemorySchedulingStateRepository,
)
from adapters.out.in_memory.remember.sitting_repository import InMemorySittingRepository
from adapters.out.in_memory.remember.unit_of_work import (
    InMemoryUnitOfWork as InMemoryRememberUnitOfWork,
)
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.claimer import InMemoryOutboxClaimer
from adapters.out.in_memory.shared.outbox.envelope_query import (
    InMemoryOutboxEnvelopeQueryAdapter,
)
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from adapters.out.llm.capture.embedding import OpenRouterEmbeddingAdapter
from adapters.out.worker.handlers.card_discard import CardDiscardHandler
from adapters.out.worker.handlers.flashcard_gen import FlashcardGenHandler
from adapters.out.worker.handlers.note_save import SaveNoteHandler
from adapters.out.worker.outbox_worker import OutboxWorker
from adapters.telemetry import configure_tracing
from application.capture.commands.approve_note import ApproveNoteCommand
from application.capture.commands.send_message import GenerateReplyCommand
from application.capture.commands.start_capture_session import (
    StartCaptureSessionCommand,
)
from application.capture.ports import EmbeddingPort, UnitOfWork
from application.capture.services.vocabulary import VocabularyResolver
from application.distill.commands.discard_card import DiscardCardCommand
from application.distill.commands.generate_cards import GenerateCardsCommand
from application.distill.commands.save_note import SaveNoteCommand
from application.distill.ports import UnitOfWork as DistillUnitOfWork
from application.distill.queries.get_note import GetNoteQueryPort
from application.distill.queries.list_cards_for_note import ListCardsForNoteQueryPort
from application.distill.queries.list_notes import ListNotesQueryPort
from application.remember.commands.grade_card import GradeCardCommand
from application.remember.commands.open_sitting import OpenSittingCommand
from application.remember.commands.reject_card import RejectCardCommand
from application.remember.commands.reveal_back import RevealBackCommand
from application.remember.ports import UnitOfWork as RememberUnitOfWork
from application.remember.queries.card_source import CardSourceQuery
from application.remember.queries.current_card import CurrentCardQuery
from application.remember.queries.due_count import DueCountQuery
from application.shared.outbox.queries.envelopes import OutboxEnvelopeQueryPort
from config.settings import EmbeddingProvider, Settings
from domain.capture.ports import CaptureSessionRepository
from domain.capture.value_objects import SimilarityScore
from domain.capture.vocabulary import MatchCriteria
from domain.distill.card_factory import CardFactory
from domain.distill.value_objects import CardLengthPolicy
from domain.remember.ports import CardSourceLocator
from domain.remember.value_objects import ResumeHorizon, ShowingLimit

_settings = Settings()  # pyright: ignore[reportCallIssue]
configure_tracing(_settings)
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
_list_notes_query = InMemoryListNotesQueryAdapter(
    _distill_note_repository, _distill_card_repository
)
_get_note_query = InMemoryGetNoteQueryAdapter(_distill_note_repository)
_list_cards_for_note_query = InMemoryListCardsForNoteQueryAdapter(
    _distill_note_repository, _distill_card_repository
)
_card_generation = DeterministicCardGenerationAdapter()
_card_factory = CardFactory(
    CardLengthPolicy(
        front_max=_settings.card_front_max, back_max=_settings.card_back_max
    )
)
_capture_agent = DeterministicCaptureAgentAdapter()


def _build_embedding_port(settings: Settings) -> EmbeddingPort:
    if settings.embedding_provider == EmbeddingProvider.DETERMINISTIC:
        return DeterministicEmbeddingAdapter()
    from pydantic_ai.embeddings import Embedder
    from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel
    from pydantic_ai.providers.openrouter import OpenRouterProvider

    embedder = Embedder(
        OpenAIEmbeddingModel(
            settings.embedding_model,
            provider=OpenRouterProvider(api_key=settings.openrouter_api_key),
        )
    )
    return OpenRouterEmbeddingAdapter(
        embedder,
        settings.embedding_model,
        settings.embedding_dimensions,
    )


_embedding = _build_embedding_port(_settings)
_vocabulary = VocabularyResolver(
    _embedding,
    MatchCriteria(
        threshold=SimilarityScore(value=_settings.vocabulary_match_threshold)
    ),
)
_remember_sittings = InMemorySittingRepository()
_remember_review_events = InMemoryReviewEventStore()
_remember_scheduling_states = InMemorySchedulingStateRepository()
_remember_lock = asyncio.Lock()
_remember_catalog = InMemoryReviewCatalog(
    _distill_note_repository, _distill_card_repository
)
_remember_card_source_locator = InMemoryCardSourceLocator(
    _distill_note_repository, _distill_card_repository
)
_remember_scheduler = FsrsScheduler()
_remember_clock = SystemClock()
_remember_showing_limit = ShowingLimit(value=_settings.sitting_max_showings)
_remember_resume_horizon = ResumeHorizon(
    value=timedelta(hours=_settings.sitting_resume_horizon_hours)
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
    card_factory=_card_factory,
)
_flashcard_gen_handler = FlashcardGenHandler(_generate_cards_command)
_discard_card_command = DiscardCardCommand(uow_factory=_distill_unit_of_work)
_card_discard_handler = CardDiscardHandler(_discard_card_command)
_outbox_worker = OutboxWorker(
    _outbox_claimer,
    [_save_note_handler, _flashcard_gen_handler, _card_discard_handler],
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
        capture_agent=_capture_agent,
        vocabulary=_vocabulary,
    )


def get_approve_note_command() -> ApproveNoteCommand:
    return ApproveNoteCommand(uow=_unit_of_work())


def get_outbox_envelope_query() -> OutboxEnvelopeQueryPort:
    return _outbox_query


def get_list_notes_query() -> ListNotesQueryPort:
    return _list_notes_query


def get_note_query() -> GetNoteQueryPort:
    return _get_note_query


def get_list_cards_for_note_query() -> ListCardsForNoteQueryPort:
    return _list_cards_for_note_query


def get_outbox_worker() -> OutboxWorker:
    return _outbox_worker


def _remember_unit_of_work() -> RememberUnitOfWork:
    return cast(
        RememberUnitOfWork,
        cast(
            object,
            InMemoryRememberUnitOfWork(
                _remember_sittings,
                _remember_review_events,
                _remember_scheduling_states,
                _outbox_store,
                _outbox_appender,
                _remember_lock,
            ),
        ),
    )


def get_open_sitting_command() -> OpenSittingCommand:
    return OpenSittingCommand(
        uow_factory=_remember_unit_of_work,
        catalog=_remember_catalog,
        clock=_remember_clock,
        showing_limit=_remember_showing_limit,
        scheduler=_remember_scheduler,
        resume_horizon=_remember_resume_horizon,
    )


def get_grade_card_command() -> GradeCardCommand:
    return GradeCardCommand(
        uow_factory=_remember_unit_of_work,
        catalog=_remember_catalog,
        scheduler=_remember_scheduler,
        clock=_remember_clock,
    )


def get_reject_card_command() -> RejectCardCommand:
    return RejectCardCommand(
        uow_factory=_remember_unit_of_work,
        catalog=_remember_catalog,
        clock=_remember_clock,
    )


def get_current_card_query() -> CurrentCardQuery:
    return CurrentCardQuery(
        _remember_sittings,
        _remember_review_events,
        _remember_catalog,
        _remember_scheduling_states,
        _remember_clock,
        _remember_scheduler,
    )


def get_due_count_query() -> DueCountQuery:
    return DueCountQuery(
        _remember_sittings,
        _remember_review_events,
        _remember_catalog,
        _remember_scheduling_states,
        _remember_clock,
        _remember_scheduler,
    )


def get_card_source_locator() -> CardSourceLocator:
    return _remember_card_source_locator


def get_card_source_query() -> CardSourceQuery:
    return CardSourceQuery(
        _remember_sittings,
        _remember_review_events,
        _remember_card_source_locator,
        _remember_clock,
    )


def get_reveal_back_command() -> RevealBackCommand:
    return RevealBackCommand(
        uow_factory=_remember_unit_of_work,
        catalog=_remember_catalog,
        clock=_remember_clock,
    )
