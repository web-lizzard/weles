import logging

from domain.capture.outbox import NOTE_APPROVED, NoteApprovedPayload
from domain.shared.outbox.model import EnvelopeType, OutboxEnvelope

logger = logging.getLogger(__name__)


class LoggingNoteSaveHandler:
    envelope_type: EnvelopeType = NOTE_APPROVED

    async def handle(self, envelope: OutboxEnvelope) -> None:
        payload = NoteApprovedPayload.model_validate(envelope.payload)
        logger.info(
            "note approved: note_id=%s session_id=%s",
            payload.note_id,
            payload.session_id,
        )
