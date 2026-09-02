from domain.capture.outbox import NOTE_APPROVED
from domain.shared.outbox.model import EnvelopeType, OutboxEnvelope


class LoggingNoteSaveHandler:
    envelope_type: EnvelopeType = NOTE_APPROVED

    async def handle(self, _envelope: OutboxEnvelope) -> None:
        raise NotImplementedError
