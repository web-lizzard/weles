from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from integration.support.in_memory_remember import InMemoryRememberComposition

from adapters.out.fsrs.scheduler import FsrsScheduler
from application.remember.commands.grade_card import GradeCardCommand
from application.remember.dto import GradeAppliedDTO
from domain.remember.exceptions import (
    CardNotInSittingError,
    CardNotPresentableError,
    SittingAlreadyCompleteError,
    SittingExpiredError,
    SittingNotFoundError,
)
from domain.remember.ports import SchedulingReplay
from domain.remember.review_event import ReviewEvent
from domain.remember.value_objects import (
    Grade,
    ResumeHorizon,
    SchedulerStamp,
    SittingId,
)

from .conftest import (
    clock_after_resume_horizon,
    open_sitting,
    reviewable,
    sitting_past_resume_horizon,
    stamp,
)


class _RaisingScheduler:
    """Forces a review() failure to prove a failed grade leaves no partial write."""

    def __init__(self, scheduler: FsrsScheduler) -> None:
        self._scheduler: FsrsScheduler = scheduler

    def stamp(self) -> SchedulerStamp:
        return self._scheduler.stamp()

    def review(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError("scheduler unavailable")


def _event(
    card_id: object,
    sitting_id: SittingId,
    grade: Grade,
    *,
    reviewed_at: datetime | None = None,
) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,  # pyright: ignore[reportArgumentType]
        reviewed_at=reviewed_at or datetime.now(UTC),
        outcome=grade,
        sitting_id=sitting_id,
    )


async def test_a_sitting_past_its_horizon_raises_expired_before_any_write(
    make_composition: Callable[..., InMemoryRememberComposition],
) -> None:
    opened_at = datetime(2026, 4, 10, 9, 0, tzinfo=UTC)
    horizon = ResumeHorizon(value=timedelta(hours=1))
    composition = make_composition(instant=clock_after_resume_horizon(opened_at))
    card = await reviewable(composition)
    sitting = sitting_past_resume_horizon(
        card, opened_at=opened_at, resume_horizon=horizon
    )
    await composition.sittings.save(sitting)

    with pytest.raises(SittingExpiredError):
        _ = await composition.grade_card().handle(sitting.id, card.id, Grade.GOOD)

    assert await composition.review_events.list_by_card(card.id) == []
    assert await composition.scheduling_states.get(card.id) is None


async def test_expiry_on_grade_is_checked_before_membership(
    make_composition: Callable[..., InMemoryRememberComposition],
) -> None:
    opened_at = datetime(2026, 4, 10, 9, 0, tzinfo=UTC)
    horizon = ResumeHorizon(value=timedelta(hours=1))
    composition = make_composition(instant=clock_after_resume_horizon(opened_at))
    member = await reviewable(composition)
    outsider = await reviewable(composition)
    sitting = sitting_past_resume_horizon(
        member, opened_at=opened_at, resume_horizon=horizon
    )
    await composition.sittings.save(sitting)

    with pytest.raises(SittingExpiredError):
        _ = await composition.grade_card().handle(sitting.id, outsider.id, Grade.GOOD)


async def test_an_unknown_sitting_raises_sitting_not_found(
    composition: InMemoryRememberComposition,
) -> None:
    card = await reviewable(composition)
    sitting = open_sitting(card)
    await composition.sittings.save(sitting)

    with pytest.raises(SittingNotFoundError):
        _ = await composition.grade_card().handle(SittingId.new(), card.id, Grade.GOOD)

    assert await composition.review_events.list_by_card(card.id) == []
    assert await composition.scheduling_states.get(card.id) is None


async def test_a_card_outside_the_sitting_raises_card_not_in_sitting(
    composition: InMemoryRememberComposition,
) -> None:
    member = await reviewable(composition)
    outsider = await reviewable(composition)
    sitting = open_sitting(member)
    await composition.sittings.save(sitting)

    with pytest.raises(CardNotInSittingError):
        _ = await composition.grade_card().handle(sitting.id, outsider.id, Grade.GOOD)

    assert await composition.review_events.list_by_card(outsider.id) == []
    assert await composition.scheduling_states.get(outsider.id) is None


async def test_a_finished_sitting_raises_already_complete_before_presentable(
    composition: InMemoryRememberComposition,
) -> None:
    card = await reviewable(composition)
    sitting = open_sitting(card)
    prior = _event(card.id, sitting.id, Grade.GOOD)
    await composition.sittings.save(sitting)
    await composition.review_events.save(prior)

    with pytest.raises(SittingAlreadyCompleteError):
        _ = await composition.grade_card().handle(sitting.id, card.id, Grade.EASY)

    assert await composition.review_events.list_by_card(card.id) == [prior]
    assert await composition.scheduling_states.get(card.id) is None


async def test_a_member_that_is_not_the_seeded_pick_raises_not_presentable(
    composition: InMemoryRememberComposition,
) -> None:
    first = await reviewable(composition, front="Alpha")
    second = await reviewable(composition, front="Beta")
    sitting = open_sitting(first, second)
    present = sitting.visible(frozenset({first.id, second.id}))
    in_front = sitting.next_card(present, events=[])
    assert in_front is not None
    other = second if in_front == first.id else first
    await composition.sittings.save(sitting)

    with pytest.raises(CardNotPresentableError):
        _ = await composition.grade_card().handle(sitting.id, other.id, Grade.FORGOT)

    assert await composition.review_events.list_by_card(other.id) == []
    assert await composition.scheduling_states.get(other.id) is None


async def test_a_stale_stamp_rebuilds_previous_from_the_card_log(
    make_composition: Callable[..., InMemoryRememberComposition],
) -> None:
    prior_at = datetime(2026, 2, 1, tzinfo=UTC)
    instant = datetime(2026, 8, 15, tzinfo=UTC)
    composition = make_composition(instant=instant)
    card = await reviewable(composition, front="Stale memo")
    sitting = open_sitting(card)
    prior = _event(card.id, sitting.id, Grade.FORGOT, reviewed_at=prior_at)
    await composition.sittings.save(sitting)
    await composition.review_events.save(prior)
    memoized_live = composition.scheduler.review(
        None, card.id, Grade.HARD, datetime(2026, 7, 1, tzinfo=UTC)
    )
    memoized = memoized_live.model_copy(
        update={"due_at": datetime(2026, 8, 1, tzinfo=UTC), "stamp": stamp("old-pin")}
    )
    await composition.scheduling_states.save(memoized)
    expected_previous = SchedulingReplay(composition.scheduler).replay(
        card.id, (prior,)
    )
    assert expected_previous is not None

    result = await composition.grade_card().handle(sitting.id, card.id, Grade.GOOD)

    # fsrs.Card() stamps a fresh internal card_id on every from-scratch replay, so
    # full-state equality is compared on the meaningful fields, not the raw payload.
    expected_next = composition.scheduler.review(
        expected_previous, card.id, Grade.GOOD, instant
    )
    from_memoized = composition.scheduler.review(memoized, card.id, Grade.GOOD, instant)
    saved = await composition.scheduling_states.get(card.id)
    assert saved is not None
    assert saved.scheduler_state.payload["stability"] == pytest.approx(
        expected_next.scheduler_state.payload["stability"]
    )
    assert saved.scheduler_state.payload["stability"] != pytest.approx(
        from_memoized.scheduler_state.payload["stability"]
    )
    assert isinstance(result, GradeAppliedDTO)
    assert result.sitting_complete is True
    assert result.next_card_id is None
    assert result.next_front is None


async def test_a_raising_scheduler_leaves_no_partial_write(
    composition: InMemoryRememberComposition,
) -> None:
    card = await reviewable(composition)
    sitting = open_sitting(card)
    await composition.sittings.save(sitting)
    command = GradeCardCommand(
        uow_factory=composition.unit_of_work,
        catalog=composition.catalog,
        scheduler=_RaisingScheduler(composition.scheduler),  # pyright: ignore[reportArgumentType]
        clock=composition.clock,
    )

    with pytest.raises(RuntimeError):
        _ = await command.handle(sitting.id, card.id, Grade.GOOD)

    assert await composition.review_events.list_by_card(card.id) == []
    assert await composition.scheduling_states.get(card.id) is None
    assert await composition.sittings.get(sitting.id) == sitting


async def test_grading_persists_exactly_the_one_submitted_write(
    composition: InMemoryRememberComposition,
) -> None:
    card = await reviewable(composition)
    sitting = open_sitting(card)
    await composition.sittings.save(sitting)

    result = await composition.grade_card().handle(sitting.id, card.id, Grade.GOOD)

    assert isinstance(result, GradeAppliedDTO)
    events = await composition.review_events.list_by_card(card.id)
    assert len(events) == 1
    assert events[0].outcome == Grade.GOOD
    state_saved = await composition.scheduling_states.get(card.id)
    assert state_saved is not None
