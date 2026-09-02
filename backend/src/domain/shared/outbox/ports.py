from typing import Protocol

from domain.shared.outbox.model import EnvelopeType, OutboxEnvelope


class OutboxAppender(Protocol):
    async def append(self, envelope: OutboxEnvelope) -> None: ...


class OutboxClaimer(Protocol):
    async def claim(
        self, envelope_type: EnvelopeType, limit: int, worker_id: str
    ) -> list[OutboxEnvelope]: ...

    async def ack(self, envelope: OutboxEnvelope) -> None: ...

    async def fail(self, envelope: OutboxEnvelope) -> None: ...
