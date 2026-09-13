import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.fsrs.scheduler import FsrsScheduler
from adapters.out.sqlalchemy.distill.unit_of_work import SqlAlchemyDistillUnitOfWork
from adapters.out.sqlalchemy.engine import create_engine, create_session_factory
from adapters.out.sqlalchemy.remember.query import (
    QueryReviewEventReader,
    QuerySchedulingStateReader,
)
from adapters.out.sqlalchemy.remember.review_catalog import SqlAlchemyReviewCatalog
from adapters.out.sqlalchemy.remember.unit_of_work import SqlAlchemyRememberUnitOfWork
from adapters.out.sqlalchemy.shared.outbox.claimer import SqlAlchemyOutboxClaimer
from application.remember.commands.grade_card import GradeCardCommand
from application.remember.commands.open_sitting import OpenSittingCommand
from application.remember.commands.reject_card import RejectCardCommand
from application.remember.dto import SittingOpenedDTO
from application.remember.ports import Clock
from domain.distill.card import Card
from domain.distill.note import mint_note
from domain.distill.value_objects import (
    Anchor,
    CardSide,
    NoteContent,
    NoteId,
    SessionId,
    TopicSnapshot,
)
from domain.distill.value_objects import (
    CardId as DistillCardId,
)
from domain.remember.outbox import CARD_REJECTED, CardRejectedPayload
from domain.remember.review_event import ReviewEvent
from domain.remember.value_objects import (
    MIN_RESUME_HORIZON,
    CardId,
    Grade,
    Graded,
    Rejection,
    ResumeHorizon,
    ShowingLimit,
    SittingId,
)

pytestmark = pytest.mark.postgres

_AS_OF = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
_FRONT = "What establishes a connection?"
_BACK = "A three-way handshake."
_ANCHOR_QUOTE = "Connections are established via a three-way handshake."
_NOTE_BODY = f"Lead paragraph.\n\n{_ANCHOR_QUOTE}\n\nTail."
_SHOWING_LIMIT = ShowingLimit(value=2)


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


async def _seed_live_card(
    session_factory: async_sessionmaker[AsyncSession],
) -> CardId:
    note_id = NoteId(value=uuid4())
    distill_card = Card(
        id=DistillCardId(value=uuid4()),
        note_id=note_id,
        front=CardSide(value=_FRONT),
        back=CardSide(value=_BACK),
        anchor=Anchor(quote=_ANCHOR_QUOTE),
        discard=None,
        created_at=_AS_OF,
    )
    async with _distill_uow_factory(session_factory) as uow:
        note = mint_note(
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
    return CardId(value=distill_card.id.value)


def _open_sitting_command(
    session_factory: async_sessionmaker[AsyncSession], clock: Clock
) -> OpenSittingCommand:
    return OpenSittingCommand(
        uow_factory=lambda: _remember_uow_factory(session_factory),  # pyright: ignore[reportArgumentType]
        catalog=SqlAlchemyReviewCatalog(session_factory),
        clock=clock,
        showing_limit=_SHOWING_LIMIT,
        scheduler=FsrsScheduler(),
        resume_horizon=ResumeHorizon(value=MIN_RESUME_HORIZON),
    )


def _grade_card_command(
    session_factory: async_sessionmaker[AsyncSession], clock: Clock
) -> GradeCardCommand:
    return GradeCardCommand(
        uow_factory=lambda: _remember_uow_factory(session_factory),  # pyright: ignore[reportArgumentType]
        catalog=SqlAlchemyReviewCatalog(session_factory),
        scheduler=FsrsScheduler(),
        clock=clock,
    )


def _reject_card_command(
    session_factory: async_sessionmaker[AsyncSession], clock: Clock
) -> RejectCardCommand:
    return RejectCardCommand(
        uow_factory=lambda: _remember_uow_factory(session_factory),  # pyright: ignore[reportArgumentType]
        catalog=SqlAlchemyReviewCatalog(session_factory),
        clock=clock,
    )


async def test_grade_after_open_sitting_persists_event_and_state_on_fresh_engine(
    engine: AsyncEngine,
    migrated_database_url: str,
) -> None:
    session_factory = create_session_factory(engine)
    clock = _FixedClock(_AS_OF)
    _ = await _seed_live_card(session_factory)

    opened = await _open_sitting_command(session_factory, clock).handle()
    assert isinstance(opened, SittingOpenedDTO)
    sitting_id = SittingId(value=opened.sitting_id)
    assert opened.card_id is not None
    card_id = CardId(value=opened.card_id)

    _ = await _grade_card_command(session_factory, clock).handle(
        sitting_id, card_id, Grade.GOOD
    )

    await engine.dispose()
    fresh_engine = create_engine(migrated_database_url)
    try:
        factory = create_session_factory(fresh_engine)
        events = await QueryReviewEventReader(factory).list_by_card(card_id)
        state = await QuerySchedulingStateReader(factory).get(card_id)
        assert len(events) == 1
        assert events[0].payload == Graded(grade=Grade.GOOD)
        assert events[0].reviewed_at == _AS_OF
        assert events[0].sitting_id == sitting_id
        assert state is not None
        assert state.card_id == card_id
        assert state.due_at > _AS_OF
    finally:
        await fresh_engine.dispose()


async def test_reject_card_commits_rejection_event_and_claimable_card_rejected_envelope(
    engine: AsyncEngine,
    migrated_database_url: str,
) -> None:
    session_factory = create_session_factory(engine)
    clock = _FixedClock(_AS_OF)
    card_id = await _seed_live_card(session_factory)

    opened = await _open_sitting_command(session_factory, clock).handle()
    assert isinstance(opened, SittingOpenedDTO)
    await _reject_card_command(session_factory, clock).handle(
        SittingId(value=opened.sitting_id), card_id
    )

    await engine.dispose()
    fresh_engine = create_engine(migrated_database_url)
    try:
        factory = create_session_factory(fresh_engine)
        events = await QueryReviewEventReader(factory).list_by_card(card_id)
        claimed = await SqlAlchemyOutboxClaimer(factory).claim(
            CARD_REJECTED, limit=10, worker_id="remember-persistence"
        )
        assert len(events) == 1
        assert events[0].payload == Rejection()
        assert events[0].reviewed_at == _AS_OF
        assert len(claimed) == 1
        assert claimed[0].payload == CardRejectedPayload(
            card_id=card_id.value, rejected_at=_AS_OF
        ).model_dump(mode="json")
    finally:
        await fresh_engine.dispose()


async def test_exception_after_event_save_and_outbox_append_leaves_neither_persisted(
    engine: AsyncEngine,
    migrated_database_url: str,
) -> None:
    session_factory = create_session_factory(engine)
    clock = _FixedClock(_AS_OF)
    card_id = await _seed_live_card(session_factory)
    opened = await _open_sitting_command(session_factory, clock).handle()
    assert isinstance(opened, SittingOpenedDTO)
    sitting_id = SittingId(value=opened.sitting_id)
    envelope = CardRejectedPayload(
        card_id=card_id.value, rejected_at=_AS_OF
    ).to_envelope()

    with pytest.raises(RuntimeError, match="boom"):
        async with _remember_uow_factory(session_factory) as uow:
            event = ReviewEvent(
                card_id=card_id,
                reviewed_at=_AS_OF,
                payload=Rejection(),
                sitting_id=sitting_id,
            )
            await uow.review_events.save(event)
            await uow.outbox.append(envelope)
            raise RuntimeError("boom")

    await engine.dispose()
    fresh_engine = create_engine(migrated_database_url)
    try:
        factory = create_session_factory(fresh_engine)
        events = await QueryReviewEventReader(factory).list_by_card(card_id)
        claimed = await SqlAlchemyOutboxClaimer(factory).claim(
            CARD_REJECTED, limit=10, worker_id="remember-persistence"
        )
        assert events == []
        assert claimed == []
    finally:
        await fresh_engine.dispose()


async def test_second_remember_uow_enters_only_after_first_transaction_ends(
    engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(engine)
    first_inside = asyncio.Event()
    first_release = asyncio.Event()
    second_entered = asyncio.Event()

    async def hold_first_transaction() -> None:
        async with _remember_uow_factory(session_factory) as uow:
            _ = first_inside.set()
            _ = await first_release.wait()
            await uow.commit()

    async def enter_second_after_first() -> None:
        _ = await first_inside.wait()
        async with _remember_uow_factory(session_factory):
            _ = second_entered.set()

    first_task = asyncio.create_task(hold_first_transaction())
    _ = await asyncio.wait_for(first_inside.wait(), timeout=2.0)
    second_task = asyncio.create_task(enter_second_after_first())
    await asyncio.sleep(0.05)
    assert not second_entered.is_set()
    _ = first_release.set()
    await first_task
    await second_task
    assert second_entered.is_set()
