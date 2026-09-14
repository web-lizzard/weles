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
from domain.shared.identity.model import UserId
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

REMEMBER_LOCK_KEY: int = 0x57454C45535F5245


class SqlAlchemyRememberUnitOfWork:
    sittings: SqlAlchemySittingRepository
    review_events: SqlAlchemyReviewEventStore
    scheduling_states: SqlAlchemySchedulingStateRepository
    outbox: SqlAlchemyOutboxAppender

    def __init__(
        self, owner: UserId, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        _ = owner
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory
        self._committed: bool = False
        self._session: AsyncSession | None = None
        _session = cast(AsyncSession, object())
        self.sittings = SqlAlchemySittingRepository(_session)
        self.review_events = SqlAlchemyReviewEventStore(_session)
        self.scheduling_states = SqlAlchemySchedulingStateRepository(_session)
        self.outbox = SqlAlchemyOutboxAppender(_session)

    async def __aenter__(self) -> "SqlAlchemyRememberUnitOfWork":
        self._committed = False
        session = self._session_factory()
        self._session = session
        _ = await session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": REMEMBER_LOCK_KEY},
        )
        self.sittings = SqlAlchemySittingRepository(session)
        self.review_events = SqlAlchemyReviewEventStore(session)
        self.scheduling_states = SqlAlchemySchedulingStateRepository(session)
        self.outbox = SqlAlchemyOutboxAppender(session)
        return self

    async def __aexit__(self, *exc: object) -> None:
        session = self._session
        if session is None:
            return
        try:
            if not self._committed:
                await session.rollback()
        finally:
            await session.close()
            self._session = None

    async def commit(self) -> None:
        session = self._session
        assert session is not None
        await session.commit()
        self._committed = True
