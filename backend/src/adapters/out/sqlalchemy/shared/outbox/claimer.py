# pyright: reportUnusedParameter=false
from domain.shared.outbox.model import EnvelopeType, OutboxEnvelope
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlAlchemyOutboxClaimer:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def claim(
        self, envelope_type: EnvelopeType, limit: int, worker_id: str
    ) -> list[OutboxEnvelope]:
        raise NotImplementedError

    async def ack(self, envelope: OutboxEnvelope) -> None:
        raise NotImplementedError

    async def fail(self, envelope: OutboxEnvelope) -> None:
        raise NotImplementedError
