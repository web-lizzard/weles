# pyright: reportUnusedParameter=false
from collections.abc import Sequence

from domain.remember.ports import ReviewableCard
from domain.remember.value_objects import CardId
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlAlchemyReviewCatalog:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def list_reviewable(self) -> Sequence[ReviewableCard]:
        raise NotImplementedError

    async def get_reviewable(self, card_id: CardId) -> ReviewableCard | None:
        raise NotImplementedError
