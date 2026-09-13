from adapters.out.sqlalchemy.remember.mapping import sitting_to_domain, sitting_to_row
from adapters.out.sqlalchemy.remember.models import (
    RememberSittingCardRow,
    RememberSittingRow,
)
from domain.remember.sitting import Sitting
from domain.remember.value_objects import SittingId
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class SqlAlchemySittingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def save(self, sitting: Sitting) -> None:
        statement = (
            select(RememberSittingRow)
            .where(RememberSittingRow.id == sitting.id)
            .options(selectinload(RememberSittingRow.cards))
        )
        existing = (await self._session.execute(statement)).scalar_one_or_none()
        if existing is None:
            self._session.add(sitting_to_row(sitting))
        else:
            existing.opened_at = sitting.opened_at
            existing.showing_limit = sitting.showing_limit
            existing.resume_horizon = sitting.resume_horizon
            _ = await self._session.execute(
                delete(RememberSittingCardRow).where(
                    RememberSittingCardRow.sitting_id == sitting.id
                )
            )
            existing.cards = [
                RememberSittingCardRow(sitting_id=sitting.id, card_id=card_id)
                for card_id in sitting.card_ids
            ]
        await self._session.flush()

    async def get(self, sitting_id: SittingId) -> Sitting | None:
        statement = (
            select(RememberSittingRow)
            .where(RememberSittingRow.id == sitting_id)
            .options(selectinload(RememberSittingRow.cards))
        )
        row = (await self._session.execute(statement)).scalar_one_or_none()
        return sitting_to_domain(row) if row is not None else None

    async def latest(self) -> Sitting | None:
        statement = (
            select(RememberSittingRow)
            .options(selectinload(RememberSittingRow.cards))
            .order_by(RememberSittingRow.opened_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(statement)).scalar_one_or_none()
        return sitting_to_domain(row) if row is not None else None
