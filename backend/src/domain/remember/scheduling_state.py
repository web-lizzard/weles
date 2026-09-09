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


def card_is_due(state: SchedulingState | None, as_of: datetime) -> bool:
    """A card is due when it has no memoized record, or due_at <= as_of."""
    ...
