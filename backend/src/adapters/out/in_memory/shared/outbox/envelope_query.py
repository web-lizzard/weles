from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from application.shared.outbox.dto import OutboxEnvelopeDTO


class InMemoryOutboxEnvelopeQueryAdapter:
    def __init__(self, store: InMemoryOutboxStore) -> None:
        self._store: InMemoryOutboxStore = store

    async def list_envelopes(self) -> list[OutboxEnvelopeDTO]:
        return [
            OutboxEnvelopeDTO(
                id=envelope.id.value,
                type=str(envelope.type),
                status=envelope.status.value,
                attempts=envelope.attempts,
                created_at=envelope.created_at,
                claimed_at=envelope.claimed_at,
                claimed_by=envelope.claimed_by,
            )
            for envelope in self._store.all()
        ]
