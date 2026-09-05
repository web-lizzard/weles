import logging
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.distill.unit_of_work import InMemoryUnitOfWork
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from adapters.out.worker.handlers.flashcard_gen import FlashcardGenHandler
from application.distill.commands.generate_cards import GenerateCardsCommand
from application.distill.value_objects import CardProposal
from domain.distill.card_factory import CardFactory
from domain.distill.note import Note, mint_note
from domain.distill.outbox import NOTE_SAVED, NoteSavedPayload
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


class _StubCardGeneration:
    def __init__(self, proposals: list[CardProposal] | None = None) -> None:
        self._proposals: list[CardProposal] = proposals or []

    async def generate(self, content: NoteContent) -> list[CardProposal]:
        del content
        return self._proposals


class _StubNoteDocumentParser:
    def __init__(self, resolved: set[str] | None = None) -> None:
        self._resolved: set[str] = resolved or set()

    async def resolves(self, content: NoteContent, quote: str) -> bool:
        del content
        return quote in self._resolved


def test_envelope_type_is_note_saved() -> None:
    assert FlashcardGenHandler.envelope_type == NOTE_SAVED


async def test_valid_envelope_dispatches_to_the_command_for_that_note() -> None:
    stack = _make_handler_stack(
        card_generation=_StubCardGeneration(
            [CardProposal(front="Q1", back="A1", quote="handshake begins")]
        ),
        parser=_StubNoteDocumentParser(resolved={"handshake begins"}),
    )
    note = await stack.seed_generating_note()
    payload = NoteSavedPayload(note_id=note.id.value)

    await stack.handler.handle(payload.to_envelope())

    persisted_note = await stack.notes_repo.get(note.id)
    assert persisted_note is not None
    assert persisted_note.distillation_status == DistillationStatus.READY
    cards = await stack.cards_repo.list_by_note(note.id)
    assert len(cards) == 1


async def test_malformed_payload_is_logged_and_not_dispatched(
    caplog: pytest.LogCaptureFixture,
) -> None:
    stack = _make_handler_stack(
        card_generation=_StubCardGeneration(), parser=_StubNoteDocumentParser()
    )
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
            NoteContent(value="A handshake begins the connection."),
            [TagSnapshot(id=uuid4(), label="networking")],
            datetime.now(UTC),
        )
        await self.notes_repo.save(note)
        return note


def _make_handler_stack(
    card_generation: _StubCardGeneration, parser: _StubNoteDocumentParser
) -> _HandlerStack:
    notes_repo = InMemoryNoteRepository()
    cards_repo = InMemoryCardRepository()
    outbox_store = InMemoryOutboxStore()
    outbox = InMemoryOutboxAppender(outbox_store)

    def uow_factory() -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(notes_repo, cards_repo, outbox_store, outbox)

    card_factory = CardFactory(CardLengthPolicy(front_max=200, back_max=600))
    command = GenerateCardsCommand(
        uow_factory,  # pyright: ignore[reportArgumentType]
        card_generation,
        parser,
        card_factory,
    )
    handler = FlashcardGenHandler(command)
    return _HandlerStack(notes_repo, cards_repo, handler)
