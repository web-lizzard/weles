from typing import Protocol

from application.shared.outbox.dto import OutboxEnvelopeDTO


class OutboxEnvelopeQueryPort(Protocol):
    async def list_envelopes(self) -> list[OutboxEnvelopeDTO]: ...
