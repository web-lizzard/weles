# pyright: reportUnusedParameter=false
from domain.remember.sitting import Sitting
from domain.remember.value_objects import SittingId
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemySittingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def save(self, sitting: Sitting) -> None:
        raise NotImplementedError

    async def get(self, sitting_id: SittingId) -> Sitting | None:
        raise NotImplementedError

    async def latest(self) -> Sitting | None:
        raise NotImplementedError
