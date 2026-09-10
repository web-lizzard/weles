from collections.abc import Mapping, Sequence
from datetime import datetime

from pydantic import BaseModel

from domain.remember.review_event import ReviewEvent
from domain.remember.scheduling_state import SchedulingState, due_card_ids
from domain.remember.sitting import Sitting
from domain.remember.value_objects import CardId, SchedulerStamp


class DuePartition(BaseModel, frozen=True):
    total: int
    not_yet_seen: int
    seen_still_owed: int
    ripe_outside_sitting: int


def partition_due(
    live_ids: frozenset[CardId],
    states: Mapping[CardId, SchedulingState | None],
    sitting: Sitting | None,
    sitting_events: Sequence[ReviewEvent],
    as_of: datetime,
    current_stamp: SchedulerStamp,
) -> DuePartition:
    due = due_card_ids(live_ids, states, as_of, current_stamp)

    if sitting is None:
        total = len(due)
        return DuePartition(
            total=total,
            not_yet_seen=total,
            seen_still_owed=0,
            ripe_outside_sitting=0,
        )

    present = sitting.visible(live_ids)
    outstanding = sitting.outstanding(present, sitting_events)
    total_set = due | outstanding

    not_yet_seen = 0
    seen_still_owed = 0
    ripe_outside_sitting = 0

    for card_id in total_set:
        if card_id in outstanding:
            if _shown_in_sitting(card_id, sitting, sitting_events):
                seen_still_owed += 1
            else:
                not_yet_seen += 1
        else:
            ripe_outside_sitting += 1

    return DuePartition(
        total=len(total_set),
        not_yet_seen=not_yet_seen,
        seen_still_owed=seen_still_owed,
        ripe_outside_sitting=ripe_outside_sitting,
    )


def _shown_in_sitting(
    card_id: CardId,
    sitting: Sitting,
    sitting_events: Sequence[ReviewEvent],
) -> bool:
    return any(
        event.card_id == card_id and event.sitting_id == sitting.id
        for event in sitting_events
    )
