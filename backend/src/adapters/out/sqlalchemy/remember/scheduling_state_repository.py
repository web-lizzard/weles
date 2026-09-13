# pyright: reportUnusedParameter=false
from collections.abc import Sequence

from domain.remember.scheduling_state import SchedulingState
from domain.remember.value_objects import CardId
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemySchedulingStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def save(self, state: SchedulingState) -> None:
        raise NotImplementedError

    async def get(self, card_id: CardId) -> SchedulingState | None:
        raise NotImplementedError

    async def get_many(
        self, card_ids: Sequence[CardId]
    ) -> dict[CardId, SchedulingState]:
        raise NotImplementedError
