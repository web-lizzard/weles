from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from domain.shared.outbox.model import OutboxEnvelope


class InMemoryOutboxAppender:
    def __init__(self, store: InMemoryOutboxStore) -> None:
        self._store: InMemoryOutboxStore = store

    async def append(self, envelope: OutboxEnvelope) -> None:
        await self._store.put(envelope)
