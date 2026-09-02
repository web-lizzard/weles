from typing import Protocol

from domain.shared.outbox.model import EnvelopeType, OutboxEnvelope


class OutboxHandler(Protocol):
    envelope_type: EnvelopeType

    async def handle(self, envelope: OutboxEnvelope) -> None: ...
