"""Phase 6: sitting handlers carry the same partition as DueCountQuery."""

from datetime import UTC, datetime

from integration.support.in_memory_remember import InMemoryRememberComposition

from application.remember.dto import (
    DuePartitionDTO,
    GradeAppliedDTO,
    PresentedCardDTO,
    SittingOpenedDTO,
    SittingResumedDTO,
)
from domain.remember.review_event import ReviewEvent
from domain.remember.value_objects import CardId, Grade, SittingId

from .conftest import open_sitting, reviewable


def _event(card_id: object, sitting_id: SittingId, grade: Grade) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,  # pyright: ignore[reportArgumentType]
        reviewed_at=datetime.now(UTC),
        outcome=grade,
        sitting_id=sitting_id,
    )


def _assert_partition_matches_oracle(
    actual: DuePartitionDTO, expected: DuePartitionDTO
) -> None:
    assert actual.total == expected.total
    assert actual.not_yet_seen == expected.not_yet_seen
    assert actual.seen_still_owed == expected.seen_still_owed
    assert actual.ripe_outside_sitting == expected.ripe_outside_sitting


async def _due_count_partition(
    composition: InMemoryRememberComposition,
) -> DuePartitionDTO:
    return (await composition.due_count().handle()).due


async def test_a_fresh_open_carries_the_live_partition_with_no_seen_still_owed(
    composition: InMemoryRememberComposition,
) -> None:
    _ = await reviewable(composition, front="One")
    _ = await reviewable(composition, front="Two")

    opened = await composition.open_sitting().handle()
    expected = await _due_count_partition(composition)

    assert isinstance(opened, SittingOpenedDTO)
    _assert_partition_matches_oracle(opened.due, expected)
    assert opened.due.seen_still_owed == 0
    assert opened.due.total == 2
    assert opened.due.not_yet_seen == 2


async def test_resuming_an_offered_sitting_carries_the_live_partition(
    composition: InMemoryRememberComposition,
) -> None:
    _ = await reviewable(composition, front="Resume me")

    _ = await composition.open_sitting().handle()
    resumed = await composition.open_sitting().handle()
    expected = await _due_count_partition(composition)

    assert isinstance(resumed, SittingResumedDTO)
    _assert_partition_matches_oracle(resumed.due, expected)


async def test_a_hard_grade_carries_the_live_partition_including_seen_still_owed(
    composition: InMemoryRememberComposition,
) -> None:
    _ = await reviewable(composition, front="Alpha")
    _ = await reviewable(composition, front="Beta")

    opened = await composition.open_sitting().handle()
    assert isinstance(opened, SittingOpenedDTO)
    assert opened.card_id is not None

    graded = await composition.grade_card().handle(
        SittingId(value=opened.sitting_id),
        CardId(value=opened.card_id),
        Grade.HARD,
    )
    expected = await _due_count_partition(composition)

    assert isinstance(graded, GradeAppliedDTO)
    _assert_partition_matches_oracle(graded.due, expected)
    assert graded.due.seen_still_owed == 1


async def test_current_card_carries_the_live_partition_for_the_sitting_state(
    composition: InMemoryRememberComposition,
) -> None:
    shown = await reviewable(composition, front="Shown already")
    unshown = await reviewable(composition, front="Still waiting")
    sitting = open_sitting(shown, unshown)
    await composition.sittings.save(sitting)
    await composition.review_events.save(_event(shown.id, sitting.id, Grade.FORGOT))

    presented = await composition.current_card().handle(sitting.id)
    expected = await _due_count_partition(composition)

    assert isinstance(presented, PresentedCardDTO)
    _assert_partition_matches_oracle(presented.due, expected)
    assert presented.due.seen_still_owed == 1
    assert presented.due.not_yet_seen == 1
