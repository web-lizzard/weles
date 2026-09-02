import asyncio
import copy
from uuid import UUID

from domain.shared.outbox.model import EnvelopeStatus, EnvelopeType, OutboxEnvelope


class InMemoryOutboxStore:
    def __init__(self) -> None:
        self._envelopes: dict[UUID, OutboxEnvelope] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    def snapshot(self) -> dict[UUID, OutboxEnvelope]:
        return copy.deepcopy(self._envelopes)

    def restore(self, snapshot: dict[UUID, OutboxEnvelope]) -> None:
        self._envelopes = copy.deepcopy(snapshot)

    async def put(self, envelope: OutboxEnvelope) -> None:
        self._envelopes[envelope.id.value] = envelope

    async def select_pending(
        self, envelope_type: EnvelopeType, limit: int
    ) -> list[OutboxEnvelope]:
        matching = [
            envelope
            for envelope in self._envelopes.values()
            if envelope.status == EnvelopeStatus.PENDING
            and envelope.type == envelope_type
        ]
        matching.sort(key=lambda envelope: envelope.created_at)
        return matching[:limit]

    def lock(self) -> asyncio.Lock:
        return self._lock

    def all(self) -> list[OutboxEnvelope]:
        return list(self._envelopes.values())
