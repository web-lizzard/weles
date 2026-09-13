from adapters.out.sqlalchemy.shared.outbox.mapping import to_envelope
from adapters.out.sqlalchemy.shared.outbox.models import OutboxEnvelopeRow
from domain.shared.outbox.model import EnvelopeStatus, EnvelopeType, OutboxEnvelope
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlAlchemyOutboxClaimer:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def claim(
        self, envelope_type: EnvelopeType, limit: int, worker_id: str
    ) -> list[OutboxEnvelope]:
        async with self._session_factory() as session, session.begin():
            statement = (
                select(OutboxEnvelopeRow)
                .where(
                    OutboxEnvelopeRow.status == EnvelopeStatus.PENDING.value,
                    OutboxEnvelopeRow.type_name == envelope_type.name,
                    OutboxEnvelopeRow.type_version == envelope_type.version,
                )
                .order_by(OutboxEnvelopeRow.created_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
            rows = (await session.execute(statement)).scalars().all()
            claimed: list[OutboxEnvelope] = []
            for row in rows:
                envelope = to_envelope(row)
                envelope.claim(worker_id)
                row.status = envelope.status.value
                row.attempts = envelope.attempts
                row.claimed_at = envelope.claimed_at
                row.claimed_by = envelope.claimed_by
                claimed.append(envelope)
            return claimed

    async def ack(self, envelope: OutboxEnvelope) -> None:
        await self._write_back(envelope)

    async def fail(self, envelope: OutboxEnvelope) -> None:
        await self._write_back(envelope)

    async def _write_back(self, envelope: OutboxEnvelope) -> None:
        async with self._session_factory() as session, session.begin():
            statement = (
                update(OutboxEnvelopeRow)
                .where(OutboxEnvelopeRow.id == envelope.id.value)
                .values(
                    status=envelope.status.value,
                    attempts=envelope.attempts,
                    claimed_at=envelope.claimed_at,
                    claimed_by=envelope.claimed_by,
                )
            )
            _ = await session.execute(statement)
