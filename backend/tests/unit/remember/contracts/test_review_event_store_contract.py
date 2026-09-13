from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from adapters.out.in_memory.remember.review_event_store import InMemoryReviewEventStore
from adapters.out.in_memory.remember.sitting_repository import InMemorySittingRepository
from adapters.out.sqlalchemy.engine import create_session_factory
from adapters.out.sqlalchemy.remember.short_session import (
    ShortSessionReviewEventStore,
    ShortSessionSittingRepository,
)
from domain.remember.ports import ReviewEventStore, SittingRepository
from domain.remember.review_event import ReviewEvent
from domain.remember.sitting import Sitting
from domain.remember.value_objects import CardId, Grade, Graded, ShowingLimit, SittingId


@dataclass
class _ReviewEventFixture:
    events: ReviewEventStore
    sittings: SittingRepository


@pytest.fixture(
    params=["in_memory", pytest.param("postgres", marks=pytest.mark.postgres)]
)
def review_event_fixture(request: pytest.FixtureRequest) -> _ReviewEventFixture:
    if request.param == "in_memory":  # pyright: ignore[reportAny]
        return _ReviewEventFixture(
            events=InMemoryReviewEventStore(),
            sittings=InMemorySittingRepository(),
        )
    engine: AsyncEngine = request.getfixturevalue("engine")  # pyright: ignore[reportAny]
    session_factory = create_session_factory(engine)
    return _ReviewEventFixture(
        events=ShortSessionReviewEventStore(session_factory),
        sittings=ShortSessionSittingRepository(session_factory),
    )


def _card_id() -> CardId:
    return CardId(value=uuid4())


def _open_sitting() -> Sitting:
    return Sitting.open(
        frozenset({_card_id()}),
        datetime.now(UTC),
        ShowingLimit(value=2),
    )


def _event(
    card_id: CardId,
    sitting_id: SittingId,
    *,
    reviewed_at: datetime,
    grade: Grade = Grade.GOOD,
) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,
        sitting_id=sitting_id,
        payload=Graded(grade=grade),
        reviewed_at=reviewed_at,
    )


async def _seed_sitting(sittings: SittingRepository) -> Sitting:
    sitting = _open_sitting()
    await sittings.save(sitting)
    return sitting


async def test_list_by_card_returns_that_card_s_events_in_reviewed_at_order(
    review_event_fixture: _ReviewEventFixture,
) -> None:
    store = review_event_fixture.events
    sitting = await _seed_sitting(review_event_fixture.sittings)
    card_id = _card_id()
    later = datetime.now(UTC)
    earlier = later - timedelta(seconds=10)
    first = _event(card_id, sitting.id, reviewed_at=earlier, grade=Grade.FORGOT)
    second = _event(card_id, sitting.id, reviewed_at=later, grade=Grade.GOOD)
    other = _event(_card_id(), sitting.id, reviewed_at=later)

    await store.save(second)
    await store.save(other)
    await store.save(first)
    result = await store.list_by_card(card_id)

    assert result == [first, second]


async def test_list_by_sitting_returns_that_sitting_s_events_in_reviewed_at_order(
    review_event_fixture: _ReviewEventFixture,
) -> None:
    store = review_event_fixture.events
    sitting = await _seed_sitting(review_event_fixture.sittings)
    later = datetime.now(UTC)
    earlier = later - timedelta(seconds=10)
    first = _event(_card_id(), sitting.id, reviewed_at=earlier)
    second = _event(_card_id(), sitting.id, reviewed_at=later)
    foreign_sitting = await _seed_sitting(review_event_fixture.sittings)
    foreign = _event(_card_id(), foreign_sitting.id, reviewed_at=later)

    await store.save(second)
    await store.save(foreign)
    await store.save(first)
    result = await store.list_by_sitting(sitting.id)

    assert result == [first, second]


async def test_list_by_card_returns_empty_when_the_card_has_no_events(
    review_event_fixture: _ReviewEventFixture,
) -> None:
    store = review_event_fixture.events
    sitting = await _seed_sitting(review_event_fixture.sittings)
    await store.save(_event(_card_id(), sitting.id, reviewed_at=datetime.now(UTC)))

    result = await store.list_by_card(_card_id())

    assert result == []


async def test_two_events_with_equal_reviewed_at_list_in_save_order(
    review_event_fixture: _ReviewEventFixture,
) -> None:
    store = review_event_fixture.events
    sitting = await _seed_sitting(review_event_fixture.sittings)
    card_id = _card_id()
    reviewed_at = datetime.now(UTC)
    first = _event(card_id, sitting.id, reviewed_at=reviewed_at, grade=Grade.FORGOT)
    second = _event(card_id, sitting.id, reviewed_at=reviewed_at, grade=Grade.GOOD)

    await store.save(first)
    await store.save(second)
    result = await store.list_by_card(card_id)

    assert result == [first, second]
