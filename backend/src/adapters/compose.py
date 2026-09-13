from datetime import timedelta
from typing import cast

from adapters.out.fsrs.scheduler import FsrsScheduler
from adapters.out.in_memory.capture.capture_agent import (
    DeterministicCaptureAgentAdapter,
)
from adapters.out.in_memory.capture.embedding import DeterministicEmbeddingAdapter
from adapters.out.in_memory.distill.structured_task import (
    DeterministicStructuredTaskAdapter,
)
from adapters.out.in_memory.remember.clock import SystemClock
from adapters.out.llm.capture.embedding import OpenRouterEmbeddingAdapter
from adapters.out.sqlalchemy.capture.unit_of_work import SqlAlchemyCaptureUnitOfWork
from adapters.out.sqlalchemy.distill.get_note_query import SqlAlchemyGetNoteQueryAdapter
from adapters.out.sqlalchemy.distill.list_cards_for_note_query import (
    SqlAlchemyListCardsForNoteQueryAdapter,
)
from adapters.out.sqlalchemy.distill.list_notes_query import (
    SqlAlchemyListNotesQueryAdapter,
)
from adapters.out.sqlalchemy.distill.unit_of_work import SqlAlchemyDistillUnitOfWork
from adapters.out.sqlalchemy.engine import create_engine, create_session_factory
from adapters.out.sqlalchemy.remember.card_source_locator import (
    SqlAlchemyCardSourceLocator,
)
from adapters.out.sqlalchemy.remember.query import (
    QueryReviewEventReader,
    QuerySchedulingStateReader,
    QuerySittingReader,
)
from adapters.out.sqlalchemy.remember.review_catalog import SqlAlchemyReviewCatalog
from adapters.out.sqlalchemy.remember.unit_of_work import SqlAlchemyRememberUnitOfWork
from adapters.out.sqlalchemy.shared.outbox.claimer import SqlAlchemyOutboxClaimer
from adapters.out.sqlalchemy.shared.outbox.envelope_query import (
    SqlAlchemyOutboxEnvelopeQueryAdapter,
)
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
from application.capture.ports import UnitOfWork
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
from config.settings import (
    CaptureAgentProvider,
    DistillTaskProvider,
    EmbeddingProvider,
    Settings,
)
from domain.capture.ports import CaptureAgentPort, EmbeddingPort
from domain.capture.value_objects import SimilarityScore
from domain.capture.vocabulary import MatchCriteria, VocabularyResolver
from domain.distill.card_factory import CardFactory
from domain.distill.ports import StructuredTaskPort
from domain.distill.regeneration import RegenerationPolicy, ThresholdTier
from domain.distill.value_objects import CardLengthPolicy
from domain.remember.ports import CardSourceLocator
from domain.remember.value_objects import ResumeHorizon, ShowingLimit

_settings = Settings()  # pyright: ignore[reportCallIssue]
configure_tracing(_settings)
_engine = create_engine(_settings.database_url)
_session_factory = create_session_factory(_engine)
_outbox_claimer = SqlAlchemyOutboxClaimer(_session_factory)
_outbox_query = SqlAlchemyOutboxEnvelopeQueryAdapter(_session_factory)
_list_notes_query = SqlAlchemyListNotesQueryAdapter(_session_factory)
_get_note_query = SqlAlchemyGetNoteQueryAdapter(_session_factory)
_list_cards_for_note_query = SqlAlchemyListCardsForNoteQueryAdapter(_session_factory)
_card_factory = CardFactory(
    CardLengthPolicy(
        front_max=_settings.card_front_max, back_max=_settings.card_back_max
    )
)


def _build_regeneration_policy(settings: Settings) -> RegenerationPolicy:
    return RegenerationPolicy(
        tiers=tuple(
            ThresholdTier(max_length=max_length, min_accepted_share=share)
            for max_length, share in settings.distill_regeneration_tiers
        )
    )


def _build_structured_task_port(settings: Settings) -> StructuredTaskPort:
    if settings.distill_task_provider == DistillTaskProvider.DETERMINISTIC:
        return DeterministicStructuredTaskAdapter()
    from pydantic_ai import Agent
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openrouter import OpenRouterProvider

    from adapters.out.llm.distill.structured_task import PydanticAiStructuredTaskAdapter

    model = OpenAIChatModel(
        settings.distill_model,
        provider=OpenRouterProvider(api_key=settings.openrouter_api_key),
    )
    agent = Agent(model=model)
    return cast(
        StructuredTaskPort,
        cast(object, PydanticAiStructuredTaskAdapter(agent, settings.distill_model)),
    )


def _build_capture_agent_port(settings: Settings) -> CaptureAgentPort:
    if settings.capture_agent_provider == CaptureAgentProvider.DETERMINISTIC:
        return DeterministicCaptureAgentAdapter()
    from pydantic_ai import Agent
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openrouter import OpenRouterProvider

    from adapters.out.llm.capture.agent import PydanticAiCaptureAgentAdapter

    model = OpenAIChatModel(
        settings.capture_model,
        provider=OpenRouterProvider(api_key=settings.openrouter_api_key),
    )
    agent = Agent(model=model)
    return cast(
        CaptureAgentPort,
        cast(object, PydanticAiCaptureAgentAdapter(agent, settings.capture_model)),
    )


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


_capture_agent = _build_capture_agent_port(_settings)
_structured_task = _build_structured_task_port(_settings)
_regeneration_policy = _build_regeneration_policy(_settings)
_embedding = _build_embedding_port(_settings)
_vocabulary = VocabularyResolver(
    _embedding,
    MatchCriteria(
        threshold=SimilarityScore(value=_settings.vocabulary_match_threshold)
    ),
)
_remember_sittings = QuerySittingReader(_session_factory)
_remember_review_events = QueryReviewEventReader(_session_factory)
_remember_scheduling_states = QuerySchedulingStateReader(_session_factory)
_remember_catalog = SqlAlchemyReviewCatalog(_session_factory)
_remember_card_source_locator = SqlAlchemyCardSourceLocator(_session_factory)
_remember_scheduler = FsrsScheduler()
_remember_clock = SystemClock()
_remember_showing_limit = ShowingLimit(value=_settings.sitting_max_showings)
_remember_resume_horizon = ResumeHorizon(
    value=timedelta(hours=_settings.sitting_resume_horizon_hours)
)


def _unit_of_work() -> UnitOfWork:
    return cast(
        UnitOfWork,
        cast(object, SqlAlchemyCaptureUnitOfWork(_session_factory)),
    )


def _distill_unit_of_work() -> DistillUnitOfWork:
    return cast(
        DistillUnitOfWork,
        cast(object, SqlAlchemyDistillUnitOfWork(_session_factory)),
    )


_save_note_command = SaveNoteCommand(uow_factory=_distill_unit_of_work)
_save_note_handler = SaveNoteHandler(_save_note_command)
_generate_cards_command = GenerateCardsCommand(
    uow_factory=_distill_unit_of_work,
    structured_task=_structured_task,
    card_factory=_card_factory,
    regeneration_policy=_regeneration_policy,
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


def get_start_capture_session_command() -> StartCaptureSessionCommand:
    return StartCaptureSessionCommand(uow=_unit_of_work())


def get_generate_reply_command() -> GenerateReplyCommand:
    return GenerateReplyCommand(
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
        cast(object, SqlAlchemyRememberUnitOfWork(_session_factory)),
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
