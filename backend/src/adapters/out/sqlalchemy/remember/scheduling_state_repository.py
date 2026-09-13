from collections.abc import Sequence

from adapters.out.sqlalchemy.remember.mapping import (
    scheduling_state_to_domain,
    scheduling_state_to_row,
)
from adapters.out.sqlalchemy.remember.models import RememberSchedulingStateRow
from domain.remember.scheduling_state import SchedulingState
from domain.remember.value_objects import CardId
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemySchedulingStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def save(self, state: SchedulingState) -> None:
        statement = select(RememberSchedulingStateRow).where(
            RememberSchedulingStateRow.card_id == state.card_id
        )
        existing = (await self._session.execute(statement)).scalar_one_or_none()
        if existing is None:
            self._session.add(scheduling_state_to_row(state))
        else:
            existing.due_at = state.due_at
            existing.scheduler_state = state.scheduler_state
            existing.stamp_algorithm = state.stamp.algorithm
            existing.stamp_parameter_version = state.stamp.parameter_version
        await self._session.flush()

    async def get(self, card_id: CardId) -> SchedulingState | None:
        statement = select(RememberSchedulingStateRow).where(
            RememberSchedulingStateRow.card_id == card_id
        )
        row = (await self._session.execute(statement)).scalar_one_or_none()
        return scheduling_state_to_domain(row) if row is not None else None

    async def get_many(
        self, card_ids: Sequence[CardId]
    ) -> dict[CardId, SchedulingState]:
        if not card_ids:
            return {}
        statement = select(RememberSchedulingStateRow).where(
            RememberSchedulingStateRow.card_id.in_(card_ids)
        )
        rows = (await self._session.execute(statement)).scalars().all()
        return {row.card_id: scheduling_state_to_domain(row) for row in rows}
