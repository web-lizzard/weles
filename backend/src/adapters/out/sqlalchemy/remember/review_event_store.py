# pyright: reportUnusedParameter=false
from collections.abc import Sequence

from domain.remember.review_event import ReviewEvent
from domain.remember.value_objects import CardId, SittingId
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyReviewEventStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def save(self, event: ReviewEvent) -> None:
        raise NotImplementedError

    async def list_by_card(self, card_id: CardId) -> Sequence[ReviewEvent]:
        raise NotImplementedError

    async def list_by_sitting(self, sitting_id: SittingId) -> Sequence[ReviewEvent]:
        raise NotImplementedError
