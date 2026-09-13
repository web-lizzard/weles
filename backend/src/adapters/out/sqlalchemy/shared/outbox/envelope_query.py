from adapters.out.sqlalchemy.shared.outbox.models import OutboxEnvelopeRow
from application.shared.outbox.dto import OutboxEnvelopeDTO
from domain.shared.outbox.model import EnvelopeType
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlAlchemyOutboxEnvelopeQueryAdapter:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def list_envelopes(self) -> list[OutboxEnvelopeDTO]:
        async with self._session_factory() as session:
            statement = select(OutboxEnvelopeRow).order_by(OutboxEnvelopeRow.created_at)
            rows = (await session.execute(statement)).scalars().all()
            return [
                OutboxEnvelopeDTO(
                    id=row.id,
                    type=str(
                        EnvelopeType(name=row.type_name, version=row.type_version)
                    ),
                    status=row.status,
                    attempts=row.attempts,
                    created_at=row.created_at,
                    claimed_at=row.claimed_at,
                    claimed_by=row.claimed_by,
                )
                for row in rows
            ]
