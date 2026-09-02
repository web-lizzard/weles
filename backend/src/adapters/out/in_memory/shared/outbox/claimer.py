from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from domain.shared.outbox.model import EnvelopeType, OutboxEnvelope


class InMemoryOutboxClaimer:
    def __init__(self, store: InMemoryOutboxStore) -> None:
        self._store: InMemoryOutboxStore = store

    async def claim(
        self, envelope_type: EnvelopeType, limit: int, worker_id: str
    ) -> list[OutboxEnvelope]:
        async with self._store.lock():
            pending = await self._store.select_pending(envelope_type, limit)
            claimed: list[OutboxEnvelope] = []
            for envelope in pending:
                envelope.claim(worker_id)
                await self._store.put(envelope)
                claimed.append(envelope)
            return claimed

    async def ack(self, envelope: OutboxEnvelope) -> None:
        await self._store.put(envelope)

    async def fail(self, envelope: OutboxEnvelope) -> None:
        await self._store.put(envelope)
