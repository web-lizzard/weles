import logging
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.distill.unit_of_work import InMemoryUnitOfWork
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from application.distill.commands.generate_cards import GenerateCardsCommand
from application.distill.value_objects import CardProposal
from domain.distill.card_factory import CardFactory
from domain.distill.note import Note, mint_note
from domain.distill.value_objects import (
    CardLengthPolicy,
    DiscardReason,
    DistillationStatus,
    NoteContent,
    NoteId,
    SessionId,
    TagSnapshot,
    TopicSnapshot,
)


class _StubCardGeneration:
    def __init__(
        self,
        proposals: list[CardProposal] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._proposals: list[CardProposal] = proposals or []
        self._error: Exception | None = error

    async def generate(self, content: NoteContent) -> list[CardProposal]:
        del content
        if self._error is not None:
            raise self._error
        return self._proposals


class _StubNoteDocumentParser:
    def __init__(
        self, resolved: set[str] | None = None, raises_for: str | None = None
    ) -> None:
        self._resolved: set[str] = resolved or set()
        self._raises_for: str | None = raises_for

    async def resolves(self, content: NoteContent, quote: str) -> bool:
        del content
        if quote == self._raises_for:
            raise RuntimeError("boom")
        return quote in self._resolved


async def test_generate_cards_persists_live_and_discarded_cards_and_reaches_ready() -> (
    None
):
    stack = _make_stack(
        card_generation=_StubCardGeneration(
            [
                CardProposal(front="Q1", back="A1", quote="handshake begins"),
                CardProposal(front="Q2", back="A2", quote="never mentioned"),
            ]
        ),
        parser=_StubNoteDocumentParser(resolved={"handshake begins"}),
    )
    note = await stack.seed_generating_note()

    await stack.command.handle(note.id)

    cards = await stack.cards_repo.list_by_note(note.id)
    live = [card for card in cards if card.discard is None]
    discarded = [card for card in cards if card.discard is not None]
    assert len(live) == 1
    assert len(discarded) == 1
    assert discarded[0].discard is not None
    assert discarded[0].discard.reason == DiscardReason.UNGROUNDED
    persisted_note = await stack.notes_repo.get(note.id)
    assert persisted_note is not None
    assert persisted_note.distillation_status == DistillationStatus.READY


async def test_generate_cards_reaches_ready_with_zero_live_cards_when_unresolved() -> (
    None
):
    stack = _make_stack(
        card_generation=_StubCardGeneration(
            [
                CardProposal(front="Q1", back="A1", quote="never mentioned"),
                CardProposal(front="Q2", back="A2", quote="also absent"),
            ]
        ),
        parser=_StubNoteDocumentParser(resolved=set()),
    )
    note = await stack.seed_generating_note()

    await stack.command.handle(note.id)

    cards = await stack.cards_repo.list_by_note(note.id)
    assert len(cards) == 2
    assert all(card.discard is not None for card in cards)
    persisted_note = await stack.notes_repo.get(note.id)
    assert persisted_note is not None
    assert persisted_note.distillation_status == DistillationStatus.READY


async def test_generate_cards_marks_note_failed_when_generation_port_raises() -> None:
    stack = _make_stack(
        card_generation=_StubCardGeneration(error=RuntimeError("generation down")),
        parser=_StubNoteDocumentParser(),
    )
    note = await stack.seed_generating_note()

    await stack.command.handle(note.id)

    cards = await stack.cards_repo.list_by_note(note.id)
    assert cards == []
    persisted_note = await stack.notes_repo.get(note.id)
    assert persisted_note is not None
    assert persisted_note.distillation_status == DistillationStatus.FAILED


async def test_generate_cards_redelivery_against_a_ready_note_is_a_logged_no_op(
    caplog: pytest.LogCaptureFixture,
) -> None:
    stack = _make_stack(
        card_generation=_StubCardGeneration(
            [CardProposal(front="Q1", back="A1", quote="handshake begins")]
        ),
        parser=_StubNoteDocumentParser(resolved={"handshake begins"}),
    )
    note = await stack.seed_generating_note()
    await stack.command.handle(note.id)

    with caplog.at_level(logging.INFO):
        await stack.command.handle(note.id)

    cards = await stack.cards_repo.list_by_note(note.id)
    assert len(cards) == 1
    assert any(
        "redeliver" in record.message.lower()
        or "no-op" in record.message.lower()
        or "no_op" in record.message.lower()
        for record in caplog.records
    )


async def test_generate_cards_rolls_back_saved_cards_when_commit_is_never_reached() -> (
    None
):
    stack = _make_stack(
        card_generation=_StubCardGeneration(
            [
                CardProposal(front="Q1", back="A1", quote="handshake begins"),
                CardProposal(front="Q2", back="A2", quote="boom trigger"),
            ]
        ),
        parser=_StubNoteDocumentParser(
            resolved={"handshake begins"}, raises_for="boom trigger"
        ),
    )
    note = await stack.seed_generating_note()

    with pytest.raises(RuntimeError):
        await stack.command.handle(note.id)

    cards = await stack.cards_repo.list_by_note(note.id)
    assert cards == []
    persisted_note = await stack.notes_repo.get(note.id)
    assert persisted_note is not None
    assert persisted_note.distillation_status == DistillationStatus.GENERATING


class _Stack:
    notes_repo: InMemoryNoteRepository
    cards_repo: InMemoryCardRepository
    command: GenerateCardsCommand

    def __init__(
        self,
        notes_repo: InMemoryNoteRepository,
        cards_repo: InMemoryCardRepository,
        command: GenerateCardsCommand,
    ) -> None:
        self.notes_repo = notes_repo
        self.cards_repo = cards_repo
        self.command = command

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


def _make_stack(
    card_generation: _StubCardGeneration, parser: _StubNoteDocumentParser
) -> _Stack:
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
    return _Stack(notes_repo, cards_repo, command)
