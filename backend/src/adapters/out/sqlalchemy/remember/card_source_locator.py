# pyright: reportUnusedParameter=false
from domain.remember.ports import CardSource
from domain.remember.value_objects import CardId
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlAlchemyCardSourceLocator:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def locate(self, card_id: CardId) -> CardSource | None:
        raise NotImplementedError
