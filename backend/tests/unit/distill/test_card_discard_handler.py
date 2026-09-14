import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import override
from uuid import uuid4

import pytest

from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.distill.unit_of_work import InMemoryUnitOfWork
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from adapters.out.worker.handlers.card_discard import CardDiscardHandler
from application.distill.commands.discard_card import DiscardCardCommand
from application.distill.ports import UnitOfWork
from domain.distill.card import Card
from domain.distill.value_objects import (
    Anchor,
    CardId,
    CardSide,
    DiscardReason,
    NoteId,
)
from domain.remember.outbox import CARD_REJECTED, CardRejectedPayload
from domain.shared.identity.model import UserId
from domain.shared.outbox.model import OutboxEnvelope


def test_envelope_type_is_card_rejected() -> None:
    assert CardDiscardHandler.envelope_type == CARD_REJECTED


async def test_valid_card_rejected_envelope_dispatches_user_audit_discard() -> None:
    stack = _make_handler_stack()
    note_id = NoteId(value=uuid4())
    card = _sample_card(note_id)
    await stack.cards_repo.save(card)
    rejected_at = datetime(2026, 5, 2, 10, 15, tzinfo=UTC)
    payload = CardRejectedPayload(card_id=card.id.value, rejected_at=rejected_at)

    await stack.handler.handle(payload.to_envelope())

    persisted = await stack.cards_repo.get(card.id)
    assert persisted is not None
    assert persisted.discard is not None
    assert persisted.discard.reason == DiscardReason.USER_AUDIT
    assert persisted.discard.discarded_at == rejected_at


async def test_malformed_card_rejected_payload_is_logged_without_calling_discard(
    caplog: pytest.LogCaptureFixture,
) -> None:
    stack = _make_handler_stack()
    note_id = NoteId(value=uuid4())
    card = _sample_card(note_id)
    await stack.cards_repo.save(card)
    recording = _RecordingDiscardCommand(
        stack.uow_factory  # pyright: ignore[reportArgumentType]
    )
    handler = CardDiscardHandler(recording)
    envelope = OutboxEnvelope.pending(CARD_REJECTED, {})

    with caplog.at_level(logging.ERROR):
        await handler.handle(envelope)

    persisted = await stack.cards_repo.get(card.id)
    assert persisted is not None
    assert persisted.discard is None
    assert recording.invoked is False
    assert any(record.levelno >= logging.ERROR for record in caplog.records)


def _sample_card(note_id: NoteId) -> Card:
    return Card(
        id=CardId(value=uuid4()),
        owner_id=UserId.new(),
        note_id=note_id,
        front=CardSide(value="What establishes a connection?"),
        back=CardSide(value="A three-way handshake."),
        anchor=Anchor(quote="Connections are established via a three-way handshake."),
        discard=None,
        created_at=datetime.now(UTC),
    )


class _RecordingDiscardCommand(DiscardCardCommand):
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        super().__init__(uow_factory)
        self.invoked: bool = False

    @override
    async def handle(
        self,
        card_id: CardId,
        reason: DiscardReason,
        detail: str | None,
        discarded_at: datetime,
    ) -> None:
        self.invoked = True
        await super().handle(card_id, reason, detail, discarded_at)


class _HandlerStack:
    cards_repo: InMemoryCardRepository
    handler: CardDiscardHandler
    uow_factory: Callable[[], InMemoryUnitOfWork]

    def __init__(
        self,
        cards_repo: InMemoryCardRepository,
        handler: CardDiscardHandler,
        uow_factory: Callable[[], InMemoryUnitOfWork],
    ) -> None:
        self.cards_repo = cards_repo
        self.handler = handler
        self.uow_factory = uow_factory


def _make_handler_stack() -> _HandlerStack:
    notes_repo = InMemoryNoteRepository()
    cards_repo = InMemoryCardRepository()
    outbox_store = InMemoryOutboxStore()
    outbox = InMemoryOutboxAppender(outbox_store)

    def uow_factory() -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(notes_repo, cards_repo, outbox_store, outbox)

    command = DiscardCardCommand(uow_factory)  # pyright: ignore[reportArgumentType]
    handler = CardDiscardHandler(command)
    return _HandlerStack(cards_repo, handler, uow_factory)
