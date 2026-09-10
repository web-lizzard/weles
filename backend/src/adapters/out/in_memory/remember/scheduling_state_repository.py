from collections.abc import Sequence

from domain.remember.scheduling_state import SchedulingState
from domain.remember.value_objects import CardId


class InMemorySchedulingStateRepository:
    def __init__(self) -> None:
        self._states: dict[CardId, SchedulingState] = {}

    async def save(self, state: SchedulingState) -> None:
        self._states[state.card_id] = state

    async def get(self, card_id: CardId) -> SchedulingState | None:
        return self._states.get(card_id)

    async def get_many(
        self, card_ids: Sequence[CardId]
    ) -> dict[CardId, SchedulingState]:
        return {
            card_id: self._states[card_id]
            for card_id in card_ids
            if card_id in self._states
        }

    def snapshot(self) -> dict[CardId, SchedulingState]:
        return dict(self._states)

    def restore(self, snapshot: dict[CardId, SchedulingState]) -> None:
        self._states = dict(snapshot)
