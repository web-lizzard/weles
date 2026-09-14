import math
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from adapters.auth.exceptions import TooManyAttemptsError
from adapters.auth.model import AttemptAction, AttemptLimits, AttemptSource
from adapters.auth.sqlalchemy_models import AuthAttemptRow


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
        self, action: AttemptAction, source: AttemptSource
    ) -> None:
        limit = self._limits.for_action(action)
        cutoff = datetime.now(UTC) - limit.window
        async with self._session_factory() as session:
            statement = select(
                func.count(), func.min(AuthAttemptRow.attempted_at)
            ).where(
                AuthAttemptRow.action == action.value,
                AuthAttemptRow.source == source.value,
                AuthAttemptRow.attempted_at >= cutoff,
            )
            row = cast(
                "tuple[int, datetime | None]",
                cast(object, (await session.execute(statement)).one()),
            )
            count, oldest = row
            if count < limit.max_attempts:
                return
            assert oldest is not None
            remaining = (oldest + limit.window) - datetime.now(UTC)
            retry_after_seconds = max(1, math.ceil(remaining.total_seconds()))
            raise TooManyAttemptsError(retry_after_seconds=retry_after_seconds)

    async def record(self, action: AttemptAction, source: AttemptSource) -> None:
        limit = self._limits.for_action(action)
        cutoff = datetime.now(UTC) - limit.window
        row = AuthAttemptRow(
            id=uuid4(),
            action=action.value,
            source=source.value,
            attempted_at=datetime.now(UTC),
        )
        async with self._session_factory() as session:
            session.add(row)
            _ = await session.execute(
                delete(AuthAttemptRow).where(
                    AuthAttemptRow.action == action.value,
                    AuthAttemptRow.source == source.value,
                    AuthAttemptRow.attempted_at < cutoff,
                )
            )
            await session.commit()

    async def clear(self, action: AttemptAction, source: AttemptSource) -> None:
        async with self._session_factory() as session:
            _ = await session.execute(
                delete(AuthAttemptRow).where(
                    AuthAttemptRow.action == action.value,
                    AuthAttemptRow.source == source.value,
                )
            )
            await session.commit()
