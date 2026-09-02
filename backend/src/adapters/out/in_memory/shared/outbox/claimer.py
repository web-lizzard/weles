from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from domain.shared.outbox.model import EnvelopeType, OutboxEnvelope


class InMemoryOutboxClaimer:
    def __init__(self, store: InMemoryOutboxStore) -> None:
        self._store: InMemoryOutboxStore = store

    async def claim(
        self, _envelope_type: EnvelopeType, _limit: int, _worker_id: str
    ) -> list[OutboxEnvelope]:
        raise NotImplementedError

    async def ack(self, _envelope: OutboxEnvelope) -> None:
        raise NotImplementedError

    async def fail(self, _envelope: OutboxEnvelope) -> None:
        raise NotImplementedError
