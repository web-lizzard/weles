from application.shared.outbox.dto import OutboxEnvelopeDTO
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlAlchemyOutboxEnvelopeQueryAdapter:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def list_envelopes(self) -> list[OutboxEnvelopeDTO]:
        raise NotImplementedError
