from adapters.out.sqlalchemy.shared.outbox.mapping import to_row
from domain.shared.outbox.model import OutboxEnvelope
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyOutboxAppender:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def append(self, envelope: OutboxEnvelope) -> None:
        self._session.add(to_row(envelope))
