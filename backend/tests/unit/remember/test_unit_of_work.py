import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from adapters.out.in_memory.remember.review_event_store import InMemoryReviewEventStore
from adapters.out.in_memory.remember.scheduling_state_repository import (
    InMemorySchedulingStateRepository,
)
from adapters.out.in_memory.remember.sitting_repository import InMemorySittingRepository
from adapters.out.in_memory.remember.unit_of_work import InMemoryUnitOfWork
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from domain.remember.review_event import ReviewEvent
from domain.remember.scheduling_state import SchedulingState
from domain.remember.sitting import Sitting
from domain.remember.value_objects import (
    CardId,
    Grade,
    Graded,
    OpaqueSchedulerState,
    SchedulerAlgorithm,
    SchedulerStamp,
    ShowingLimit,
)


def _make_unit_of_work() -> tuple[
    InMemoryUnitOfWork,
    InMemorySittingRepository,
    InMemoryReviewEventStore,
    InMemorySchedulingStateRepository,
]:
    sittings = InMemorySittingRepository()
    review_events = InMemoryReviewEventStore()
    scheduling_states = InMemorySchedulingStateRepository()
    outbox_store = InMemoryOutboxStore()
    uow = InMemoryUnitOfWork(
        sittings,
        review_events,
        scheduling_states,
        outbox_store,
        InMemoryOutboxAppender(outbox_store),
        asyncio.Lock(),
    )
    return uow, sittings, review_events, scheduling_states


def _sitting() -> Sitting:
    return Sitting.open(
        frozenset({CardId(value=uuid4())}),
        datetime.now(UTC),
        ShowingLimit(value=2),
    )


def _event(card_id: CardId) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,
        sitting_id=_sitting().id,
        payload=Graded(grade=Grade.GOOD),
        reviewed_at=datetime.now(UTC),
    )


def _state(card_id: CardId) -> SchedulingState:
    return SchedulingState(
        card_id=card_id,
        due_at=datetime.now(UTC),
        scheduler_state=OpaqueSchedulerState(payload={}),
        stamp=SchedulerStamp(
            algorithm=SchedulerAlgorithm.FSRS,
            parameter_version="fsrs-6.3.2-defaults",
        ),
    )


async def test_rollback_without_commit_discards_sittings_events_and_states() -> None:
    uow, sittings, review_events, scheduling_states = _make_unit_of_work()
    sitting = _sitting()
    event = _event(next(iter(sitting.card_ids)))
    state = _state(next(iter(sitting.card_ids)))

    async with uow:
        await sittings.save(sitting)
        await review_events.save(event)
        await scheduling_states.save(state)
        assert await sittings.get(sitting.id) == sitting
        assert await review_events.list_by_card(event.card_id) == [event]
        assert await scheduling_states.get(state.card_id) == state

    assert await sittings.get(sitting.id) is None
    assert await review_events.list_by_card(event.card_id) == []
    assert await scheduling_states.get(state.card_id) is None


async def test_commit_persists_sittings_events_and_states() -> None:
    uow, sittings, review_events, scheduling_states = _make_unit_of_work()
    sitting = _sitting()
    event = _event(next(iter(sitting.card_ids)))
    state = _state(next(iter(sitting.card_ids)))

    async with uow:
        await sittings.save(sitting)
        await review_events.save(event)
        await scheduling_states.save(state)
        await uow.commit()

    assert await sittings.get(sitting.id) == sitting
    assert await review_events.list_by_card(event.card_id) == [event]
    assert await scheduling_states.get(state.card_id) == state


async def test_a_second_unit_of_work_enters_only_after_the_first_window_closes() -> (
    None
):
    lock = asyncio.Lock()
    sittings = InMemorySittingRepository()
    review_events = InMemoryReviewEventStore()
    scheduling_states = InMemorySchedulingStateRepository()
    outbox_store = InMemoryOutboxStore()
    outbox = InMemoryOutboxAppender(outbox_store)
    first = InMemoryUnitOfWork(
        sittings,
        review_events,
        scheduling_states,
        outbox_store,
        outbox,
        lock,
    )
    second = InMemoryUnitOfWork(
        sittings,
        review_events,
        scheduling_states,
        outbox_store,
        outbox,
        lock,
    )
    order: list[str] = []

    async def first_window() -> None:
        async with first:
            order.append("first entered")
            await asyncio.sleep(0)
            order.append("first leaving")
            await first.commit()

    async def second_window() -> None:
        async with second:
            order.append("second entered")
            await second.commit()

    _ = await asyncio.gather(first_window(), second_window())

    assert order == ["first entered", "first leaving", "second entered"]
