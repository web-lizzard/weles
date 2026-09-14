from collections.abc import Sequence

from adapters.out.sqlalchemy.distill.models import DistillCardRow
from domain.distill.value_objects import CardId as DistillCardId
from domain.remember.ports import ReviewableCard
from domain.remember.value_objects import CardId
from domain.shared.identity.model import UserId
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlAlchemyReviewCatalog:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def list_reviewable(self, owner: UserId) -> Sequence[ReviewableCard]:
        _ = owner
        async with self._session_factory() as session:
            rows = (
                (
                    await session.execute(
                        select(DistillCardRow)
                        .where(DistillCardRow.discard_reason.is_(None))
                        .order_by(DistillCardRow.created_at, DistillCardRow.id)
                    )
                )
                .scalars()
                .all()
            )
            return [_as_reviewable(row) for row in rows]

    async def get_reviewable(
        self, owner: UserId, card_id: CardId
    ) -> ReviewableCard | None:
        _ = owner
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    select(DistillCardRow).where(
                        DistillCardRow.id == DistillCardId(value=card_id.value),
                        DistillCardRow.discard_reason.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if row is None:
                return None
            return _as_reviewable(row)


def _as_reviewable(row: DistillCardRow) -> ReviewableCard:
    return ReviewableCard(
        id=CardId(value=row.id.value),
        front=row.front.value,
        back=row.back.value,
    )
