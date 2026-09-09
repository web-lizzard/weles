# pyright: reportUnusedParameter=false
from datetime import datetime

from pydantic import BaseModel

from domain.remember.value_objects import (
    CardId,
    OpaqueSchedulerState,
    SchedulerStamp,
)


class SchedulingState(BaseModel, frozen=True):
    card_id: CardId
    due_at: datetime
    scheduler_state: OpaqueSchedulerState
    stamp: SchedulerStamp


def card_is_due(
    state: SchedulingState | None,
    as_of: datetime,
    current_stamp: SchedulerStamp,
) -> bool:
    """Due when there is no record, the stamp is stale, or due_at <= as_of."""
    if state is None:
        return True
    if state.stamp != current_stamp:
        return True
    return state.due_at <= as_of
