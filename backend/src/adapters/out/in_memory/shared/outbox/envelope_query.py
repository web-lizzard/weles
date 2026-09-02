from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from application.shared.outbox.dto import OutboxEnvelopeDTO


class InMemoryOutboxEnvelopeQueryAdapter:
    def __init__(self, store: InMemoryOutboxStore) -> None:
        self._store: InMemoryOutboxStore = store

    async def list_envelopes(self) -> list[OutboxEnvelopeDTO]:
        raise NotImplementedError
