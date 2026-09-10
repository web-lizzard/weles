# pyright: reportUnusedParameter=false
from collections.abc import Mapping, Sequence
from datetime import datetime

from pydantic import BaseModel

from domain.remember.review_event import ReviewEvent
from domain.remember.scheduling_state import SchedulingState
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
    raise NotImplementedError
