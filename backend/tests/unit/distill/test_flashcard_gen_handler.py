import json
import logging
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from pydantic_ai import Agent, models
from pydantic_ai.models.test import TestModel

from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.distill.structured_task import (
    DeterministicStructuredTaskAdapter,
)
from adapters.out.in_memory.distill.unit_of_work import InMemoryUnitOfWork
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from adapters.out.llm.distill.structured_task import PydanticAiStructuredTaskAdapter
from adapters.out.llm.tracing import OBSERVATION_INPUT, OBSERVATION_TYPE, SESSION_ID
from adapters.out.worker.handlers.flashcard_gen import FlashcardGenHandler
from application.distill.commands.generate_cards import GenerateCardsCommand
from domain.distill.card_factory import CardFactory
from domain.distill.note import Note, mint_note
from domain.distill.outbox import NOTE_SAVED, NoteSavedPayload
from domain.distill.ports import StructuredTaskPort
from domain.distill.regeneration import RegenerationPolicy, ThresholdTier
from domain.distill.value_objects import (
    CardLengthPolicy,
    DistillationStatus,
    NoteContent,
    NoteId,
    SessionId,
    TagSnapshot,
    TopicSnapshot,
)
from domain.shared.outbox.model import OutboxEnvelope

models.ALLOW_MODEL_REQUESTS = False

_RESOLVING_NOTE = NoteContent(value="A handshake begins the connection.")


def _install_in_memory_tracer() -> InMemorySpanExporter:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return exporter


def _never_regenerate_policy() -> RegenerationPolicy:
    return RegenerationPolicy(
        tiers=(ThresholdTier(max_length=None, min_accepted_share=0.0),)
    )


def test_envelope_type_is_note_saved() -> None:
    assert FlashcardGenHandler.envelope_type == NOTE_SAVED


async def test_valid_envelope_dispatches_to_the_command_for_that_note() -> None:
    stack = _make_handler_stack()
    note = await stack.seed_generating_note()
    payload = NoteSavedPayload(note_id=note.id.value)

    await stack.handler.handle(payload.to_envelope())

    persisted_note = await stack.notes_repo.get(note.id)
    assert persisted_note is not None
    assert persisted_note.distillation_status == DistillationStatus.READY
    cards = await stack.cards_repo.list_by_note(note.id)
    assert len(cards) >= 1


async def test_handle_exports_distill_run_chain_span_with_note_id_as_session() -> None:
    exporter = _install_in_memory_tracer()
    stack = _make_handler_stack()
    note = await stack.seed_generating_note()
    payload = NoteSavedPayload(note_id=note.id.value)

    await stack.handler.handle(payload.to_envelope())

    spans = exporter.get_finished_spans()
    run_spans = [span for span in spans if span.name == "distill_run"]
    assert len(run_spans) == 1
    run_span = run_spans[0]
    attributes = run_span.attributes
    assert attributes is not None
    assert attributes[OBSERVATION_TYPE] == "chain"
    assert attributes[SESSION_ID] == str(note.id.value)
    observation_input = attributes[OBSERVATION_INPUT]
    assert isinstance(observation_input, str)
    assert json.loads(observation_input) == {"note_id": str(note.id.value)}


async def test_handle_nests_structured_task_spans_under_distill_run() -> None:
    exporter = _install_in_memory_tracer()
    stack = _make_pydantic_handler_stack()
    note = await stack.seed_generating_note()
    payload = NoteSavedPayload(note_id=note.id.value)

    await stack.handler.handle(payload.to_envelope())

    spans = exporter.get_finished_spans()
    run_spans = [span for span in spans if span.name == "distill_run"]
    assert len(run_spans) == 1
    run_span = run_spans[0]
    run_context = run_span.get_span_context()
    assert run_context is not None
    run_span_id = run_context.span_id
    task_spans = [span for span in spans if span.name != "distill_run"]
    assert task_spans
    for task_span in task_spans:
        parent_context = task_span.parent
        assert parent_context is not None
        assert parent_context.span_id == run_span_id


async def test_malformed_payload_is_logged_and_not_dispatched(
    caplog: pytest.LogCaptureFixture,
) -> None:
    stack = _make_handler_stack()
    note = await stack.seed_generating_note()
    envelope = OutboxEnvelope.pending(NOTE_SAVED, {})

    with caplog.at_level(logging.ERROR):
        await stack.handler.handle(envelope)

    persisted_note = await stack.notes_repo.get(note.id)
    assert persisted_note is not None
    assert persisted_note.distillation_status == DistillationStatus.GENERATING
    assert await stack.cards_repo.list_by_note(note.id) == []
    assert any(record.levelno >= logging.ERROR for record in caplog.records)


class _HandlerStack:
    notes_repo: InMemoryNoteRepository
    cards_repo: InMemoryCardRepository
    handler: FlashcardGenHandler

    def __init__(
        self,
        notes_repo: InMemoryNoteRepository,
        cards_repo: InMemoryCardRepository,
        handler: FlashcardGenHandler,
    ) -> None:
        self.notes_repo = notes_repo
        self.cards_repo = cards_repo
        self.handler = handler

    async def seed_generating_note(self) -> Note:
        note = mint_note(
            NoteId(value=uuid4()),
            SessionId(value=uuid4()),
            TopicSnapshot(id=uuid4(), label="TCP handshakes"),
            _RESOLVING_NOTE,
            [TagSnapshot(id=uuid4(), label="networking")],
            datetime.now(UTC),
        )
        await self.notes_repo.save(note)
        return note


def _make_handler_stack() -> _HandlerStack:
    return _handler_stack_with_structured_task(DeterministicStructuredTaskAdapter())


def _make_pydantic_handler_stack() -> _HandlerStack:
    adapter = PydanticAiStructuredTaskAdapter(
        Agent(model=TestModel()),
        model_name="openai/gpt-4o-mini",
    )
    return _handler_stack_with_structured_task(adapter)


def _handler_stack_with_structured_task(
    structured_task: StructuredTaskPort,
) -> _HandlerStack:
    notes_repo = InMemoryNoteRepository()
    cards_repo = InMemoryCardRepository()
    outbox_store = InMemoryOutboxStore()
    outbox = InMemoryOutboxAppender(outbox_store)

    def uow_factory() -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(notes_repo, cards_repo, outbox_store, outbox)

    card_factory = CardFactory(CardLengthPolicy(front_max=200, back_max=600))
    command = GenerateCardsCommand(
        uow_factory=uow_factory,  # pyright: ignore[reportArgumentType]
        structured_task=structured_task,
        card_factory=card_factory,
        regeneration_policy=_never_regenerate_policy(),
    )
    handler = FlashcardGenHandler(command)
    return _HandlerStack(notes_repo, cards_repo, handler)
