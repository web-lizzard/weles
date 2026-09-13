import logging
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import pytest
from pydantic import BaseModel

from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.distill.unit_of_work import InMemoryUnitOfWork
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from application.distill.commands.generate_cards import GenerateCardsCommand
from domain.distill.card_factory import CardFactory
from domain.distill.note import Note, mint_note
from domain.distill.regeneration import RegenerationPolicy, ThresholdTier
from domain.distill.run import CardsProposed, CardsReviewed, DistillEvent
from domain.distill.value_objects import (
    CandidateRef,
    CardLengthPolicy,
    CardProposal,
    CardVerdict,
    DiscardReason,
    DistillationStatus,
    NoteContent,
    NoteId,
    ReviewGrade,
    SessionId,
    TagSnapshot,
    TopicSnapshot,
)
from domain.shared.instruction.model import Instruction

_RESOLVING_NOTE = NoteContent(value="A handshake begins the connection.")


class _ScriptedStructuredTask:
    """Scripts exact port answers for outcomes the deterministic adapter
    cannot reach on demand: a chosen review grade, and a failure partway
    through a run."""

    def __init__(self, *answers: DistillEvent, error: Exception | None = None) -> None:
        self._answers: list[DistillEvent] = list(answers)
        self._error: Exception | None = error
        self._calls: int = 0

    async def complete[OutputT: BaseModel](
        self, instruction: Instruction, output: type[OutputT]
    ) -> OutputT:
        del instruction, output
        if self._calls < len(self._answers):
            answer = self._answers[self._calls]
            self._calls += 1
            return cast(OutputT, answer)
        if self._error is not None:
            raise self._error
        raise AssertionError("structured task called more times than scripted")


async def test_generate_cards_persists_live_and_discarded_cards_and_reaches_ready() -> (
    None
):
    structured_task = _ScriptedStructuredTask(
        CardsProposed(
            proposals=[
                CardProposal(front="Q1", back="A1", quote="handshake begins"),
                CardProposal(front="Q2", back="A2", quote="never mentioned"),
            ]
        ),
        CardsReviewed(
            verdicts=[
                CardVerdict(
                    ref=CandidateRef(value="c1"),
                    grade=ReviewGrade.SOUND,
                    reasoning="grounded and self-contained",
                )
            ]
        ),
    )
    stack = _make_stack(structured_task)
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
    structured_task = _ScriptedStructuredTask(
        CardsProposed(
            proposals=[
                CardProposal(front="Q1", back="A1", quote="never mentioned"),
                CardProposal(front="Q2", back="A2", quote="also absent"),
            ]
        )
    )
    stack = _make_stack(structured_task)
    note = await stack.seed_generating_note()

    await stack.command.handle(note.id)

    cards = await stack.cards_repo.list_by_note(note.id)
    assert len(cards) == 2
    assert all(card.discard is not None for card in cards)
    persisted_note = await stack.notes_repo.get(note.id)
    assert persisted_note is not None
    assert persisted_note.distillation_status == DistillationStatus.READY


async def test_generate_cards_marks_failed_nothing_persisted_on_mid_flow_error() -> (
    None
):
    structured_task = _ScriptedStructuredTask(
        CardsProposed(
            proposals=[CardProposal(front="Q1", back="A1", quote="handshake begins")]
        ),
        error=RuntimeError("review provider down"),
    )
    stack = _make_stack(structured_task)
    note = await stack.seed_generating_note()

    await stack.command.handle(note.id)

    cards = await stack.cards_repo.list_by_note(note.id)
    assert cards == []
    persisted_note = await stack.notes_repo.get(note.id)
    assert persisted_note is not None
    assert persisted_note.distillation_status == DistillationStatus.FAILED


async def test_generate_cards_missing_note_is_a_logged_no_op(
    caplog: pytest.LogCaptureFixture,
) -> None:
    stack = _make_stack(_ScriptedStructuredTask())
    unknown_note_id = NoteId(value=uuid4())

    with caplog.at_level(logging.INFO):
        await stack.command.handle(unknown_note_id)

    assert any("not found" in record.message.lower() for record in caplog.records)


async def test_generate_cards_redelivery_against_a_ready_note_is_a_logged_no_op(
    caplog: pytest.LogCaptureFixture,
) -> None:
    structured_task = _ScriptedStructuredTask(
        CardsProposed(
            proposals=[CardProposal(front="Q1", back="A1", quote="handshake begins")]
        ),
        CardsReviewed(
            verdicts=[
                CardVerdict(
                    ref=CandidateRef(value="c1"),
                    grade=ReviewGrade.SOUND,
                    reasoning="grounded and self-contained",
                )
            ]
        ),
    )
    stack = _make_stack(structured_task)
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
            _RESOLVING_NOTE,
            [TagSnapshot(id=uuid4(), label="networking")],
            datetime.now(UTC),
        )
        await self.notes_repo.save(note)
        return note


def _never_regenerate_policy() -> RegenerationPolicy:
    return RegenerationPolicy(
        tiers=(ThresholdTier(max_length=None, min_accepted_share=0.0),)
    )


def _make_stack(structured_task: _ScriptedStructuredTask) -> _Stack:
    notes_repo = InMemoryNoteRepository()
    cards_repo = InMemoryCardRepository()
    outbox_store = InMemoryOutboxStore()
    outbox = InMemoryOutboxAppender(outbox_store)

    def uow_factory() -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(notes_repo, cards_repo, outbox_store, outbox)

    card_factory = CardFactory(CardLengthPolicy(front_max=200, back_max=600))
    command = GenerateCardsCommand(  # pyright: ignore[reportCallIssue]
        uow_factory=uow_factory,
        structured_task=structured_task,  # pyright: ignore[reportCallIssue]
        card_factory=card_factory,
        regeneration_policy=_never_regenerate_policy(),  # pyright: ignore[reportCallIssue]
    )
    return _Stack(notes_repo, cards_repo, command)
