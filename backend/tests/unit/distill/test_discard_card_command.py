import logging
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.distill.unit_of_work import InMemoryUnitOfWork
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from application.distill.commands.discard_card import DiscardCardCommand
from domain.distill.card import Card
from domain.distill.value_objects import (
    Anchor,
    CardId,
    CardSide,
    Discard,
    DiscardReason,
    NoteId,
)


def _sample_card(note_id: NoteId, discard: Discard | None = None) -> Card:
    return Card(
        id=CardId(value=uuid4()),
        note_id=note_id,
        front=CardSide(value="What establishes a connection?"),
        back=CardSide(value="A three-way handshake."),
        anchor=Anchor(quote="Connections are established via a three-way handshake."),
        discard=discard,
        created_at=datetime.now(UTC),
    )


async def test_discard_stamps_user_audit_carrying_the_envelope_discarded_at() -> None:
    stack = _make_stack()
    note_id = NoteId(value=uuid4())
    card = _sample_card(note_id)
    await stack.cards_repo.save(card)
    discarded_at = datetime(2026, 5, 1, 14, 30, tzinfo=UTC)

    await stack.command.handle(
        card.id,
        DiscardReason.USER_AUDIT,
        None,
        discarded_at,
    )

    persisted = await stack.cards_repo.get(card.id)
    assert persisted is not None
    assert persisted.discard is not None
    assert persisted.discard.reason == DiscardReason.USER_AUDIT
    assert persisted.discard.detail is None
    assert persisted.discard.discarded_at == discarded_at


async def test_discard_stamps_a_non_none_detail_onto_the_card() -> None:
    "Discard.detail must equal the handle() detail argument, including a non-None string."  # noqa: E501
    stack = _make_stack()
    note_id = NoteId(value=uuid4())
    card = _sample_card(note_id)
    await stack.cards_repo.save(card)
    discarded_at = datetime(2026, 5, 1, 14, 30, tzinfo=UTC)

    await stack.command.handle(
        card.id,
        DiscardReason.USER_AUDIT,
        "rejected during review",
        discarded_at,
    )

    persisted = await stack.cards_repo.get(card.id)
    assert persisted is not None
    assert persisted.discard is not None
    assert persisted.discard.detail == "rejected during review"


async def test_discard_leaves_a_card_that_already_carries_any_discard_unchanged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    stack = _make_stack()
    note_id = NoteId(value=uuid4())
    original_discarded_at = datetime(2026, 4, 1, 9, 0, tzinfo=UTC)
    card = _sample_card(
        note_id,
        discard=Discard(
            reason=DiscardReason.UNGROUNDED,
            detail=None,
            discarded_at=original_discarded_at,
        ),
    )
    await stack.cards_repo.save(card)
    redelivery_at = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

    with caplog.at_level(logging.INFO):
        await stack.command.handle(
            card.id,
            DiscardReason.USER_AUDIT,
            None,
            redelivery_at,
        )

    persisted = await stack.cards_repo.get(card.id)
    assert persisted == card
    assert any(
        "no-op" in record.message.lower() or "redeliver" in record.message.lower()
        for record in caplog.records
    )


async def test_discard_is_a_no_op_when_the_card_id_names_no_card(
    caplog: pytest.LogCaptureFixture,
) -> None:
    stack = _make_stack()
    missing_id = CardId(value=uuid4())

    with caplog.at_level(logging.INFO):
        await stack.command.handle(
            missing_id,
            DiscardReason.USER_AUDIT,
            None,
            datetime.now(UTC),
        )

    assert stack.cards_repo.snapshot() == {}
    assert any(
        "no-op" in record.message.lower() or "not found" in record.message.lower()
        for record in caplog.records
    )


class _DiscardStack:
    cards_repo: InMemoryCardRepository
    command: DiscardCardCommand

    def __init__(
        self,
        cards_repo: InMemoryCardRepository,
        command: DiscardCardCommand,
    ) -> None:
        self.cards_repo = cards_repo
        self.command = command


def _make_stack() -> _DiscardStack:
    notes_repo = InMemoryNoteRepository()
    cards_repo = InMemoryCardRepository()
    outbox_store = InMemoryOutboxStore()
    outbox = InMemoryOutboxAppender(outbox_store)

    def uow_factory() -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(notes_repo, cards_repo, outbox_store, outbox)

    command = DiscardCardCommand(uow_factory)  # pyright: ignore[reportArgumentType]
    return _DiscardStack(cards_repo, command)
