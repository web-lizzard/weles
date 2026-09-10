# pyright: reportUnusedParameter=false
from collections.abc import Mapping
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


def due_card_ids(
    card_ids: frozenset[CardId],
    states: Mapping[CardId, SchedulingState | None],
    as_of: datetime,
    current_stamp: SchedulerStamp,
) -> frozenset[CardId]:
    """Ids in card_ids for which card_is_due is true.

    OpenSittingCommand's mint path. Missing map entries are no record (due).
    """
    return frozenset(
        card_id
        for card_id in card_ids
        if card_is_due(states.get(card_id), as_of, current_stamp)
    )
