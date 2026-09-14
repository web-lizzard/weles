from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from integration.support.in_memory_remember import InMemoryRememberComposition

from domain.remember.review_event import ReviewEvent
from domain.remember.value_objects import Grade, Graded, ResumeHorizon, SittingId

from .conftest import (
    OWNER,
    clock_after_resume_horizon,
    open_sitting,
    reviewable,
    sitting_past_resume_horizon,
    stamp,
    state,
)


def _event(card_id: object, sitting_id: SittingId, grade: Grade) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,  # pyright: ignore[reportArgumentType]
        reviewed_at=datetime.now(UTC),
        payload=Graded(grade=grade),
        sitting_id=sitting_id,
    )


async def test_without_a_sitting_due_reviewable_cards_land_entirely_in_not_yet_seen(
    composition: InMemoryRememberComposition,
) -> None:
    _ = await reviewable(composition, front="Due now")
    _ = await reviewable(composition, front="Also due")

    result = await composition.due_count().handle(OWNER)

    assert result.due.total == 2
    assert result.due.not_yet_seen == 2
    assert result.due.seen_still_owed == 0
    assert result.due.ripe_outside_sitting == 0


async def test_a_future_due_at_excludes_the_card_from_the_total(
    composition: InMemoryRememberComposition,
) -> None:
    as_of = composition.clock.now()
    live = stamp()
    _ = await reviewable(composition, front="Due now")
    later = await reviewable(composition, front="Scheduled later")
    await composition.scheduling_states.save(
        state(later.id, due_at=as_of + timedelta(days=30), stamp=live)
    )

    result = await composition.due_count().handle(OWNER)

    assert result.due.total == 1
    assert result.due.not_yet_seen == 1


async def test_reading_the_due_count_writes_no_sitting(
    composition: InMemoryRememberComposition,
) -> None:
    _ = await reviewable(composition, front="Waiting")
    before_sittings = composition.sittings.snapshot()
    before_events = composition.review_events.snapshot()

    _ = await composition.due_count().handle(OWNER)

    assert composition.sittings.snapshot() == before_sittings
    assert composition.review_events.snapshot() == before_events


async def test_a_sitting_past_its_horizon_is_absent_from_the_partition_readings(
    make_composition: Callable[..., InMemoryRememberComposition],
) -> None:
    opened_at = datetime(2026, 4, 10, 9, 0, tzinfo=UTC)
    horizon = ResumeHorizon(value=timedelta(hours=1))
    composition = make_composition(instant=clock_after_resume_horizon(opened_at))
    in_sitting = await reviewable(composition, front="In the old sitting")
    _ = await reviewable(composition, front="Ripe outside")
    sitting = sitting_past_resume_horizon(
        in_sitting, opened_at=opened_at, resume_horizon=horizon
    )
    await composition.sittings.save(sitting)

    result = await composition.due_count().handle(OWNER)

    assert result.due.total == 2
    assert result.due.not_yet_seen == 2
    assert result.due.seen_still_owed == 0
    assert result.due.ripe_outside_sitting == 0


async def test_an_offered_sitting_buckets_shown_outstanding_into_seen_still_owed(
    composition: InMemoryRememberComposition,
) -> None:
    shown = await reviewable(composition, front="Already shown")
    unshown = await reviewable(composition, front="Still in queue")
    sitting = open_sitting(shown, unshown)
    await composition.sittings.save(sitting)
    await composition.review_events.save(_event(shown.id, sitting.id, Grade.FORGOT))

    result = await composition.due_count().handle(OWNER)

    assert result.due.total == 2
    assert result.due.not_yet_seen == 1
    assert result.due.seen_still_owed == 1
    assert result.due.ripe_outside_sitting == 0
