from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from adapters.auth.model import AttemptAction, AttemptLimits, AttemptSource


class SqlAlchemyAttemptLedger:
    """`AttemptLedger` on Postgres. Auth has no application layer and no
    `UnitOfWork`: each call is one session and commit against `auth_attempts`."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        limits: AttemptLimits,
    ) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory
        self._limits: AttemptLimits = limits

    async def ensure_allowed(
        self, _action: AttemptAction, _source: AttemptSource
    ) -> None:
        raise NotImplementedError

    async def record(self, _action: AttemptAction, _source: AttemptSource) -> None:
        raise NotImplementedError

    async def clear(self, _action: AttemptAction, _source: AttemptSource) -> None:
        raise NotImplementedError
