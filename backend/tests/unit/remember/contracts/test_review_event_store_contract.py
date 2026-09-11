from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import pytest

from adapters.out.in_memory.remember.review_event_store import InMemoryReviewEventStore
from domain.remember.ports import ReviewEventStore
from domain.remember.review_event import ReviewEvent
from domain.remember.value_objects import CardId, Grade, SittingId

_IMPLEMENTATIONS: list[Callable[[], ReviewEventStore]] = [
    cast(Callable[[], ReviewEventStore], InMemoryReviewEventStore),
]


def _card_id() -> CardId:
    return CardId(value=uuid4())


def _sitting_id() -> SittingId:
    return SittingId(value=uuid4())


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
        outcome=grade,
        reviewed_at=reviewed_at,
    )


@pytest.mark.parametrize("make_store", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_list_by_card_returns_that_card_s_events_in_reviewed_at_order(
    make_store: Callable[[], ReviewEventStore],
) -> None:
    store = make_store()
    card_id = _card_id()
    sitting_id = _sitting_id()
    later = datetime.now(UTC)
    earlier = later - timedelta(seconds=10)
    first = _event(card_id, sitting_id, reviewed_at=earlier, grade=Grade.FORGOT)
    second = _event(card_id, sitting_id, reviewed_at=later, grade=Grade.GOOD)
    other = _event(_card_id(), sitting_id, reviewed_at=later)

    await store.save(second)
    await store.save(other)
    await store.save(first)
    result = await store.list_by_card(card_id)

    assert result == [first, second]


@pytest.mark.parametrize("make_store", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_list_by_sitting_returns_that_sitting_s_events_in_reviewed_at_order(
    make_store: Callable[[], ReviewEventStore],
) -> None:
    store = make_store()
    sitting_id = _sitting_id()
    later = datetime.now(UTC)
    earlier = later - timedelta(seconds=10)
    first = _event(_card_id(), sitting_id, reviewed_at=earlier)
    second = _event(_card_id(), sitting_id, reviewed_at=later)
    foreign = _event(_card_id(), _sitting_id(), reviewed_at=later)

    await store.save(second)
    await store.save(foreign)
    await store.save(first)
    result = await store.list_by_sitting(sitting_id)

    assert result == [first, second]


@pytest.mark.parametrize("make_store", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_list_by_card_returns_empty_when_the_card_has_no_events(
    make_store: Callable[[], ReviewEventStore],
) -> None:
    store = make_store()
    await store.save(_event(_card_id(), _sitting_id(), reviewed_at=datetime.now(UTC)))

    result = await store.list_by_card(_card_id())

    assert result == []
