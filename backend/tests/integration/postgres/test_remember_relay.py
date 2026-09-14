from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.fsrs.scheduler import FsrsScheduler
from adapters.out.sqlalchemy.distill.card_repository import SqlAlchemyCardRepository
from adapters.out.sqlalchemy.distill.unit_of_work import SqlAlchemyDistillUnitOfWork
from adapters.out.sqlalchemy.engine import create_engine, create_session_factory
from adapters.out.sqlalchemy.remember.review_catalog import SqlAlchemyReviewCatalog
from adapters.out.sqlalchemy.remember.unit_of_work import SqlAlchemyRememberUnitOfWork
from adapters.out.sqlalchemy.shared.outbox.claimer import SqlAlchemyOutboxClaimer
from adapters.out.worker.handlers.card_discard import CardDiscardHandler
from adapters.out.worker.outbox_worker import OutboxWorker
from application.distill.commands.discard_card import DiscardCardCommand
from application.remember.commands.open_sitting import OpenSittingCommand
from application.remember.commands.reject_card import RejectCardCommand
from application.remember.dto import SittingOpenedDTO
from application.remember.ports import Clock
from domain.distill.card import Card
from domain.distill.note import mint_note
from domain.distill.value_objects import (
    Anchor,
    CardSide,
    DiscardReason,
    NoteContent,
    NoteId,
    SessionId,
    TopicSnapshot,
)
from domain.distill.value_objects import (
    CardId as DistillCardId,
)
from domain.remember.outbox import CARD_REJECTED
from domain.remember.value_objects import (
    MIN_RESUME_HORIZON,
    CardId,
    ResumeHorizon,
    ShowingLimit,
    SittingId,
)
from domain.shared.identity.model import UserId

pytestmark = pytest.mark.postgres

_AS_OF = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
_FRONT = "What establishes a connection?"
_BACK = "A three-way handshake."
_ANCHOR_QUOTE = "Connections are established via a three-way handshake."
_NOTE_BODY = f"Lead paragraph.\n\n{_ANCHOR_QUOTE}\n\nTail."
_OUTBOX_BATCH_SIZE = 10
_OUTBOX_MAX_ATTEMPTS = 3
_OUTBOX_WORKER_ID = "remember-test-worker"


class _FixedClock:
    def __init__(self, instant: datetime) -> None:
        self._instant: datetime = instant

    def now(self) -> datetime:
        return self._instant


def _distill_uow_factory(
    session_factory: async_sessionmaker[AsyncSession],
) -> SqlAlchemyDistillUnitOfWork:
    return SqlAlchemyDistillUnitOfWork(session_factory)


def _remember_uow_factory(
    session_factory: async_sessionmaker[AsyncSession],
) -> SqlAlchemyRememberUnitOfWork:
    return SqlAlchemyRememberUnitOfWork(session_factory)


def _relay_worker(
    session_factory: async_sessionmaker[AsyncSession],
) -> OutboxWorker:
    def distill_uow() -> SqlAlchemyDistillUnitOfWork:
        return _distill_uow_factory(session_factory)

    card_discard_handler = CardDiscardHandler(
        DiscardCardCommand(distill_uow)  # pyright: ignore[reportArgumentType]
    )
    return OutboxWorker(
        SqlAlchemyOutboxClaimer(session_factory),
        [card_discard_handler],
        worker_id=_OUTBOX_WORKER_ID,
        batch_size=_OUTBOX_BATCH_SIZE,
        max_attempts=_OUTBOX_MAX_ATTEMPTS,
    )


async def _seed_live_card(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[CardId, Card]:
    note_id = NoteId(value=uuid4())
    distill_card = Card(
        id=DistillCardId(value=uuid4()),
        owner_id=UserId.new(),
        note_id=note_id,
        front=CardSide(value=_FRONT),
        back=CardSide(value=_BACK),
        anchor=Anchor(quote=_ANCHOR_QUOTE),
        discard=None,
        created_at=_AS_OF,
    )
    async with _distill_uow_factory(session_factory) as uow:
        note = mint_note(
            UserId.new(),
            note_id,
            SessionId(value=uuid4()),
            TopicSnapshot(id=uuid4(), label="Networking"),
            NoteContent(value=_NOTE_BODY),
            [],
            _AS_OF,
        )
        await uow.notes.save(note)
        await uow.cards.save(distill_card)
        await uow.commit()
    return CardId(value=distill_card.id.value), distill_card


async def _load_distill_card(
    session_factory: async_sessionmaker[AsyncSession], card_id: DistillCardId
) -> Card | None:
    async with session_factory() as session:
        return await SqlAlchemyCardRepository(session).get(card_id)


async def test_reject_and_run_once_discards_distill_card_and_acks_envelope(
    engine: AsyncEngine,
    migrated_database_url: str,
) -> None:
    session_factory = create_session_factory(engine)
    clock: Clock = _FixedClock(_AS_OF)
    card_id, distill_card = await _seed_live_card(session_factory)
    catalog = SqlAlchemyReviewCatalog(session_factory)

    opened = await OpenSittingCommand(
        uow_factory=lambda: _remember_uow_factory(session_factory),  # pyright: ignore[reportArgumentType]
        catalog=catalog,
        clock=clock,
        showing_limit=ShowingLimit(value=2),
        scheduler=FsrsScheduler(),
        resume_horizon=ResumeHorizon(value=MIN_RESUME_HORIZON),
    ).handle()
    assert isinstance(opened, SittingOpenedDTO)

    await RejectCardCommand(
        uow_factory=lambda: _remember_uow_factory(session_factory),  # pyright: ignore[reportArgumentType]
        catalog=catalog,
        clock=clock,
    ).handle(SittingId(value=opened.sitting_id), card_id)

    acked = await _relay_worker(session_factory).run_once()
    assert acked == 1

    await engine.dispose()
    fresh_engine = create_engine(migrated_database_url)
    try:
        factory = create_session_factory(fresh_engine)
        persisted = await _load_distill_card(factory, distill_card.id)
        assert persisted is not None
        assert persisted.discard is not None
        assert persisted.discard.reason == DiscardReason.USER_AUDIT
        assert persisted.discard.discarded_at == _AS_OF

        reviewable = await SqlAlchemyReviewCatalog(factory).list_reviewable()
        assert reviewable == []

        claimed = await SqlAlchemyOutboxClaimer(factory).claim(
            CARD_REJECTED, limit=10, worker_id="relay-check"
        )
        assert claimed == []
    finally:
        await fresh_engine.dispose()
