from typing import cast

from adapters.out.sqlalchemy.remember.review_event_store import (
    SqlAlchemyReviewEventStore,
)
from adapters.out.sqlalchemy.remember.scheduling_state_repository import (
    SqlAlchemySchedulingStateRepository,
)
from adapters.out.sqlalchemy.remember.sitting_repository import (
    SqlAlchemySittingRepository,
)
from adapters.out.sqlalchemy.shared.outbox.appender import SqlAlchemyOutboxAppender
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

REMEMBER_LOCK_KEY: int = 0x57454C45535F5245


class SqlAlchemyRememberUnitOfWork:
    sittings: SqlAlchemySittingRepository
    review_events: SqlAlchemyReviewEventStore
    scheduling_states: SqlAlchemySchedulingStateRepository
    outbox: SqlAlchemyOutboxAppender

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory
        _session = cast(AsyncSession, object())
        self.sittings = SqlAlchemySittingRepository(_session)
        self.review_events = SqlAlchemyReviewEventStore(_session)
        self.scheduling_states = SqlAlchemySchedulingStateRepository(_session)
        self.outbox = SqlAlchemyOutboxAppender(_session)

    async def __aenter__(self) -> "SqlAlchemyRememberUnitOfWork":
        raise NotImplementedError

    async def __aexit__(self, *exc: object) -> None:
        raise NotImplementedError

    async def commit(self) -> None:
        raise NotImplementedError
