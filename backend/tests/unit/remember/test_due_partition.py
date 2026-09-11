from datetime import UTC, datetime, timedelta
from uuid import uuid4

from domain.remember.due_partition import DuePartition, partition_due
from domain.remember.review_event import ReviewEvent
from domain.remember.scheduling_state import SchedulingState
from domain.remember.sitting import Sitting
from domain.remember.value_objects import (
    CardId,
    Grade,
    OpaqueSchedulerState,
    SchedulerAlgorithm,
    SchedulerStamp,
    ShowingLimit,
    SittingId,
)


def _stamp(parameter_version: str = "fsrs-6.3.2-defaults") -> SchedulerStamp:
    return SchedulerStamp(
        algorithm=SchedulerAlgorithm.FSRS,
        parameter_version=parameter_version,
    )


def _card_id() -> CardId:
    return CardId(value=uuid4())


def _state(
    card_id: CardId, *, due_at: datetime, stamp: SchedulerStamp
) -> SchedulingState:
    return SchedulingState(
        card_id=card_id,
        due_at=due_at,
        scheduler_state=OpaqueSchedulerState(payload={}),
        stamp=stamp,
    )


def _open_sitting(*card_ids: CardId) -> Sitting:
    return Sitting.open(
        frozenset(card_ids),
        datetime.now(UTC),
        ShowingLimit(value=2),
    )


def _event(card_id: CardId, sitting_id: SittingId, grade: Grade) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,
        reviewed_at=datetime.now(UTC),
        outcome=grade,
        sitting_id=sitting_id,
    )


def _assert_partition_invariant(partition: DuePartition) -> None:
    assert partition.not_yet_seen >= 0
    assert partition.seen_still_owed >= 0
    assert partition.ripe_outside_sitting >= 0
    assert (
        partition.not_yet_seen
        + partition.seen_still_owed
        + partition.ripe_outside_sitting
        == partition.total
    )


def test_without_a_sitting_the_whole_total_lands_in_not_yet_seen() -> None:
    as_of = datetime.now(UTC)
    stamp = _stamp()
    due_card = _card_id()
    not_due = _card_id()
    live = frozenset({due_card, not_due})
    states = {
        not_due: _state(not_due, due_at=as_of + timedelta(days=1), stamp=stamp),
    }

    partition = partition_due(live, states, None, (), as_of, stamp)

    _assert_partition_invariant(partition)
    assert partition.total == 1
    assert partition.not_yet_seen == 1
    assert partition.seen_still_owed == 0
    assert partition.ripe_outside_sitting == 0


def test_with_a_sitting_unshown_outstanding_cards_land_in_not_yet_seen() -> None:
    as_of = datetime.now(UTC)
    stamp = _stamp()
    first = _card_id()
    second = _card_id()
    live = frozenset({first, second})
    sitting = _open_sitting(first, second)

    partition = partition_due(live, {}, sitting, (), as_of, stamp)

    _assert_partition_invariant(partition)
    assert partition.total == 2
    assert partition.not_yet_seen == 2
    assert partition.seen_still_owed == 0
    assert partition.ripe_outside_sitting == 0


def test_a_shown_outstanding_card_in_a_sitting_lands_in_seen_still_owed() -> None:
    as_of = datetime.now(UTC)
    stamp = _stamp()
    shown = _card_id()
    unshown = _card_id()
    live = frozenset({shown, unshown})
    sitting = _open_sitting(shown, unshown)
    events = (_event(shown, sitting.id, Grade.FORGOT),)

    partition = partition_due(live, {}, sitting, events, as_of, stamp)

    _assert_partition_invariant(partition)
    assert partition.total == 2
    assert partition.not_yet_seen == 1
    assert partition.seen_still_owed == 1
    assert partition.ripe_outside_sitting == 0


def test_due_cards_outside_a_sitting_land_in_ripe_outside_sitting() -> None:
    as_of = datetime.now(UTC)
    stamp = _stamp()
    in_sitting = _card_id()
    ripe = _card_id()
    live = frozenset({in_sitting, ripe})
    sitting = _open_sitting(in_sitting)

    partition = partition_due(live, {}, sitting, (), as_of, stamp)

    _assert_partition_invariant(partition)
    assert partition.total == 2
    assert partition.not_yet_seen == 1
    assert partition.seen_still_owed == 0
    assert partition.ripe_outside_sitting == 1


def test_outstanding_but_not_scheduler_due_still_counts_in_a_sitting() -> None:
    as_of = datetime.now(UTC)
    stamp = _stamp()
    card = _card_id()
    live = frozenset({card})
    states = {card: _state(card, due_at=as_of + timedelta(days=30), stamp=stamp)}
    sitting = _open_sitting(card)

    partition = partition_due(live, states, sitting, (), as_of, stamp)

    _assert_partition_invariant(partition)
    assert partition.total == 1
    assert partition.not_yet_seen == 1
    assert partition.seen_still_owed == 0
    assert partition.ripe_outside_sitting == 0


def test_mixed_buckets_partition_the_due_union_without_overlap() -> None:
    as_of = datetime.now(UTC)
    stamp = _stamp()
    unshown_outstanding = _card_id()
    seen_still_owed_card = _card_id()
    ripe = _card_id()
    live = frozenset({unshown_outstanding, seen_still_owed_card, ripe})
    sitting = _open_sitting(unshown_outstanding, seen_still_owed_card)
    events = (_event(seen_still_owed_card, sitting.id, Grade.HARD),)

    partition = partition_due(live, {}, sitting, events, as_of, stamp)

    _assert_partition_invariant(partition)
    assert partition.total == 3
    assert partition.not_yet_seen == 1
    assert partition.seen_still_owed == 1
    assert partition.ripe_outside_sitting == 1
