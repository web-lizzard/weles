import asyncio
import copy
from uuid import UUID

from domain.shared.outbox.model import EnvelopeType, OutboxEnvelope


class InMemoryOutboxStore:
    def __init__(self) -> None:
        self._envelopes: dict[UUID, OutboxEnvelope] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    def snapshot(self) -> dict[UUID, OutboxEnvelope]:
        return copy.deepcopy(self._envelopes)

    def restore(self, snapshot: dict[UUID, OutboxEnvelope]) -> None:
        self._envelopes = copy.deepcopy(snapshot)

    async def put(self, _envelope: OutboxEnvelope) -> None:
        raise NotImplementedError

    async def select_pending(
        self, _envelope_type: EnvelopeType, _limit: int
    ) -> list[OutboxEnvelope]:
        raise NotImplementedError

    def lock(self) -> asyncio.Lock:
        return self._lock

    def all(self) -> list[OutboxEnvelope]:
        return list(self._envelopes.values())
