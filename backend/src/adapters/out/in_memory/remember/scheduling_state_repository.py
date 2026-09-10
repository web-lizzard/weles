# pyright: reportUnusedParameter=false
from collections.abc import Sequence

from domain.remember.scheduling_state import SchedulingState
from domain.remember.value_objects import CardId


class InMemorySchedulingStateRepository:
    def __init__(self) -> None: ...

    async def save(self, state: SchedulingState) -> None: ...

    async def get(self, card_id: CardId) -> SchedulingState | None: ...

    async def get_many(
        self, card_ids: Sequence[CardId]
    ) -> dict[CardId, SchedulingState]: ...

    def snapshot(self) -> dict[CardId, SchedulingState]: ...

    def restore(self, snapshot: dict[CardId, SchedulingState]) -> None: ...
