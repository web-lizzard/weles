from collections.abc import Sequence

from adapters.out.sqlalchemy.remember.mapping import (
    review_event_to_domain,
    review_event_to_row,
)
from adapters.out.sqlalchemy.remember.models import RememberReviewEventRow
from domain.remember.review_event import ReviewEvent
from domain.remember.value_objects import CardId, SittingId
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyReviewEventStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def save(self, event: ReviewEvent) -> None:
        self._session.add(review_event_to_row(event))
        await self._session.flush()

    async def list_by_card(self, card_id: CardId) -> Sequence[ReviewEvent]:
        statement = (
            select(RememberReviewEventRow)
            .where(RememberReviewEventRow.card_id == card_id)
            .order_by(
                RememberReviewEventRow.reviewed_at,
                RememberReviewEventRow.id,
            )
        )
        rows = (await self._session.execute(statement)).scalars().all()
        return [review_event_to_domain(row) for row in rows]

    async def list_by_sitting(self, sitting_id: SittingId) -> Sequence[ReviewEvent]:
        statement = (
            select(RememberReviewEventRow)
            .where(RememberReviewEventRow.sitting_id == sitting_id)
            .order_by(
                RememberReviewEventRow.reviewed_at,
                RememberReviewEventRow.id,
            )
        )
        rows = (await self._session.execute(statement)).scalars().all()
        return [review_event_to_domain(row) for row in rows]
