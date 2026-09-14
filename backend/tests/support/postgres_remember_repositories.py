from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from adapters.out.sqlalchemy.remember.review_event_store import (
    SqlAlchemyReviewEventStore,
)
from adapters.out.sqlalchemy.remember.scheduling_state_repository import (
    SqlAlchemySchedulingStateRepository,
)
from adapters.out.sqlalchemy.remember.sitting_repository import (
    SqlAlchemySittingRepository,
)
from domain.remember.review_event import ReviewEvent
from domain.remember.scheduling_state import SchedulingState
from domain.remember.sitting import Sitting
from domain.remember.value_objects import CardId, SittingId
from domain.shared.identity.model import UserId


class CommittingSittingRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def save(self, sitting: Sitting) -> None:
        async with self._session_factory() as session:
            await SqlAlchemySittingRepository(session).save(sitting)
            await session.commit()

    async def get(self, sitting_id: SittingId) -> Sitting | None:
        async with self._session_factory() as session:
            return await SqlAlchemySittingRepository(session).get(sitting_id)

    async def latest(self, owner: UserId) -> Sitting | None:
        async with self._session_factory() as session:
            return await SqlAlchemySittingRepository(session).latest(owner)


class CommittingReviewEventStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def save(self, event: ReviewEvent) -> None:
        async with self._session_factory() as session:
            await SqlAlchemyReviewEventStore(session).save(event)
            await session.commit()

    async def list_by_card(self, card_id: CardId) -> Sequence[ReviewEvent]:
        async with self._session_factory() as session:
            return await SqlAlchemyReviewEventStore(session).list_by_card(card_id)

    async def list_by_sitting(self, sitting_id: SittingId) -> Sequence[ReviewEvent]:
        async with self._session_factory() as session:
            return await SqlAlchemyReviewEventStore(session).list_by_sitting(sitting_id)


class CommittingSchedulingStateRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def save(self, state: SchedulingState) -> None:
        async with self._session_factory() as session:
            await SqlAlchemySchedulingStateRepository(session).save(state)
            await session.commit()

    async def get(self, card_id: CardId) -> SchedulingState | None:
        async with self._session_factory() as session:
            return await SqlAlchemySchedulingStateRepository(session).get(card_id)

    async def get_many(
        self, card_ids: Sequence[CardId]
    ) -> dict[CardId, SchedulingState]:
        async with self._session_factory() as session:
            return await SqlAlchemySchedulingStateRepository(session).get_many(card_ids)
