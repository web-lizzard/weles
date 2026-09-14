from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.fsrs.scheduler import PARAMETER_VERSION, FsrsScheduler
from adapters.out.sqlalchemy.distill.unit_of_work import SqlAlchemyDistillUnitOfWork
from adapters.out.sqlalchemy.engine import create_session_factory
from adapters.out.sqlalchemy.remember.card_source_locator import (
    SqlAlchemyCardSourceLocator,
)
from adapters.out.sqlalchemy.remember.query import (
    QueryReviewEventReader,
    QuerySchedulingStateReader,
    QuerySittingReader,
)
from adapters.out.sqlalchemy.remember.review_catalog import SqlAlchemyReviewCatalog
from application.distill.commands.discard_card import DiscardCardCommand
from application.remember.dto import PresentedCardDTO
from application.remember.ports import Clock
from application.remember.queries.card_source import CardSourceQuery
from application.remember.queries.current_card import CurrentCardQuery
from application.remember.queries.due_count import DueCountQuery
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
from domain.remember.review_event import ReviewEvent
from domain.remember.scheduling_state import SchedulingState
from domain.remember.sitting import Sitting
from domain.remember.value_objects import (
    CardId,
    OpaqueSchedulerState,
    ResumeHorizon,
    Reveal,
    SchedulerAlgorithm,
    SchedulerStamp,
    ShowingLimit,
)
from domain.shared.identity.model import UserId
from tests.support.postgres_remember_repositories import (
    CommittingReviewEventStore,
    CommittingSchedulingStateRepository,
    CommittingSittingRepository,
)

pytestmark = pytest.mark.postgres

_AS_OF = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
_FRONT = "What establishes a connection?"
_BACK = "A three-way handshake."
_ANCHOR_QUOTE = "Connections are established via a three-way handshake."
_NOTE_BODY = f"Lead paragraph.\n\n{_ANCHOR_QUOTE}\n\nTail."
_OWNER = UserId.new()


class _FixedClock:
    def __init__(self, instant: datetime) -> None:
        self._instant: datetime = instant

    def now(self) -> datetime:
        return self._instant


def _distill_uow_factory(
    session_factory: async_sessionmaker[AsyncSession],
) -> SqlAlchemyDistillUnitOfWork:
    return SqlAlchemyDistillUnitOfWork(session_factory)


def _scheduler_stamp() -> SchedulerStamp:
    return SchedulerStamp(
        algorithm=SchedulerAlgorithm.FSRS,
        parameter_version=PARAMETER_VERSION,
    )


async def _seed_live_card(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    front: str = _FRONT,
    back: str = _BACK,
) -> tuple[CardId, Card]:
    note_id = NoteId(value=uuid4())
    distill_card = Card(
        id=DistillCardId(value=uuid4()),
        owner_id=_OWNER,
        note_id=note_id,
        front=CardSide(value=front),
        back=CardSide(value=back),
        anchor=Anchor(quote=_ANCHOR_QUOTE),
        discard=None,
        created_at=_AS_OF,
    )
    async with _distill_uow_factory(session_factory) as uow:
        note = mint_note(
            _OWNER,
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


def _remember_queries(
    session_factory: async_sessionmaker[AsyncSession],
    clock: Clock,
) -> tuple[DueCountQuery, CurrentCardQuery, CardSourceQuery, SqlAlchemyReviewCatalog]:
    scheduler = FsrsScheduler()
    sittings = QuerySittingReader(session_factory)
    events = QueryReviewEventReader(session_factory)
    states = QuerySchedulingStateReader(session_factory)
    catalog = SqlAlchemyReviewCatalog(session_factory)
    locator = SqlAlchemyCardSourceLocator(session_factory)
    due_count = DueCountQuery(sittings, events, catalog, states, clock, scheduler)
    current_card = CurrentCardQuery(sittings, events, catalog, states, clock, scheduler)
    card_source = CardSourceQuery(sittings, events, locator, clock)
    return due_count, current_card, card_source, catalog


async def test_due_count_counts_unscheduled_cards_and_honors_future_due_at(
    engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(engine)
    clock = _FixedClock(_AS_OF)
    due_count, _, _, _ = _remember_queries(session_factory, clock)
    _card_id, _ = await _seed_live_card(session_factory)
    later_id, _ = await _seed_live_card(session_factory, front="Scheduled later")
    states = CommittingSchedulingStateRepository(session_factory)
    await states.save(
        SchedulingState(
            card_id=later_id,
            due_at=_AS_OF + timedelta(days=30),
            scheduler_state=OpaqueSchedulerState(payload={}),
            stamp=_scheduler_stamp(),
        )
    )

    result = await due_count.handle(_OWNER)

    assert result.due.total == 1
    assert result.due.not_yet_seen == 1
    assert result.due.seen_still_owed == 0


async def test_current_card_presents_the_sitting_s_only_card_while_offered(
    engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(engine)
    clock = _FixedClock(_AS_OF)
    _, current_card, _, _ = _remember_queries(session_factory, clock)
    card_id, _ = await _seed_live_card(session_factory)
    sitting = Sitting.open(
        _OWNER,
        frozenset({card_id}),
        _AS_OF,
        ShowingLimit(value=2),
        resume_horizon=ResumeHorizon(value=timedelta(hours=26)),
    )
    await CommittingSittingRepository(session_factory).save(sitting)

    result = await current_card.handle(_OWNER, sitting.id)

    assert isinstance(result, PresentedCardDTO)
    assert result.card_id == card_id.value
    assert result.front == _FRONT
    assert result.sitting_complete is False


async def test_card_source_returns_blocks_and_span_after_a_reveal_event(
    engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(engine)
    clock = _FixedClock(_AS_OF)
    _, _, card_source, _ = _remember_queries(session_factory, clock)
    card_id, _ = await _seed_live_card(session_factory)
    sitting = Sitting.open(
        _OWNER,
        frozenset({card_id}),
        _AS_OF,
        ShowingLimit(value=2),
        resume_horizon=ResumeHorizon(value=timedelta(hours=26)),
    )
    sittings = CommittingSittingRepository(session_factory)
    events = CommittingReviewEventStore(session_factory)
    await sittings.save(sitting)
    await events.save(
        ReviewEvent(
            card_id=card_id,
            reviewed_at=_AS_OF,
            payload=Reveal(),
            sitting_id=sitting.id,
        )
    )

    result = await card_source.handle(_OWNER, sitting.id, card_id)

    assert len(result.blocks) == 3
    assert result.blocks[1].text == _ANCHOR_QUOTE
    assert result.span.block_index == 1


async def test_catalog_stops_offering_a_card_after_distill_discards_it(
    engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(engine)
    clock = _FixedClock(_AS_OF)
    _, _, _, catalog = _remember_queries(session_factory, clock)
    card_id, distill_card = await _seed_live_card(session_factory)

    before = await catalog.list_reviewable(_OWNER)
    assert {entry.id for entry in before} == {card_id}

    await DiscardCardCommand(
        lambda: _distill_uow_factory(session_factory)  # pyright: ignore[reportArgumentType]
    ).handle(
        distill_card.id,
        DiscardReason.USER_AUDIT,
        None,
        _AS_OF,
    )

    after = await catalog.list_reviewable(_OWNER)
    assert after == []
