# pyright: reportUnusedParameter=false
from collections.abc import Sequence

from domain.remember.review_event import ReviewEvent
from domain.remember.scheduling_state import SchedulingState
from domain.remember.sitting import Sitting
from domain.remember.value_objects import CardId, SittingId
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class ShortSessionSittingRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def save(self, sitting: Sitting) -> None:
        raise NotImplementedError

    async def get(self, sitting_id: SittingId) -> Sitting | None:
        raise NotImplementedError

    async def latest(self) -> Sitting | None:
        raise NotImplementedError


class ShortSessionReviewEventStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def save(self, event: ReviewEvent) -> None:
        raise NotImplementedError

    async def list_by_card(self, card_id: CardId) -> Sequence[ReviewEvent]:
        raise NotImplementedError

    async def list_by_sitting(self, sitting_id: SittingId) -> Sequence[ReviewEvent]:
        raise NotImplementedError


class ShortSessionSchedulingStateRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def save(self, state: SchedulingState) -> None:
        raise NotImplementedError

    async def get(self, card_id: CardId) -> SchedulingState | None:
        raise NotImplementedError

    async def get_many(
        self, card_ids: Sequence[CardId]
    ) -> dict[CardId, SchedulingState]:
        raise NotImplementedError
