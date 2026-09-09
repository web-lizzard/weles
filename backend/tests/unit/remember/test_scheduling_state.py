from datetime import UTC, datetime, timedelta
from uuid import uuid4

from domain.remember.scheduling_state import SchedulingState, card_is_due
from domain.remember.value_objects import (
    CardId,
    OpaqueSchedulerState,
    SchedulerAlgorithm,
    SchedulerStamp,
)


def _stamp(parameter_version: str = "fsrs-6.3.2-defaults") -> SchedulerStamp:
    return SchedulerStamp(
        algorithm=SchedulerAlgorithm.FSRS,
        parameter_version=parameter_version,
    )


def _state(*, due_at: datetime, stamp: SchedulerStamp) -> SchedulingState:
    return SchedulingState(
        card_id=CardId(value=uuid4()),
        due_at=due_at,
        scheduler_state=OpaqueSchedulerState(payload={}),
        stamp=stamp,
    )


def test_a_card_with_no_memoized_record_is_due() -> None:
    as_of = datetime.now(UTC)

    assert card_is_due(None, as_of, _stamp()) is True  # pyright: ignore[reportCallIssue]


def test_a_card_whose_stamp_does_not_match_the_live_scheduler_is_due() -> None:
    as_of = datetime.now(UTC)
    stale = _state(due_at=as_of + timedelta(days=30), stamp=_stamp("old-pin"))

    assert card_is_due(stale, as_of, _stamp("live-pin")) is True  # pyright: ignore[reportCallIssue]


def test_when_the_stamp_matches_due_ness_follows_whether_due_at_has_been_reached() -> (
    None
):
    as_of = datetime.now(UTC)
    stamp = _stamp()
    due_now = _state(due_at=as_of, stamp=stamp)
    due_later = _state(due_at=as_of + timedelta(seconds=1), stamp=stamp)

    assert card_is_due(due_now, as_of, stamp) is True  # pyright: ignore[reportCallIssue]
    assert card_is_due(due_later, as_of, stamp) is False  # pyright: ignore[reportCallIssue]
