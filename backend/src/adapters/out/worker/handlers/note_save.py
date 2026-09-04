import logging

from application.distill.commands.save_note import SaveNoteCommand
from domain.capture.outbox import NOTE_APPROVED, NoteApprovedPayload
from domain.shared.outbox.model import EnvelopeType, OutboxEnvelope

logger = logging.getLogger(__name__)


class SaveNoteHandler:
    envelope_type: EnvelopeType = NOTE_APPROVED

    def __init__(self, command: SaveNoteCommand) -> None:
        self._command: SaveNoteCommand = command

    async def handle(self, _envelope: OutboxEnvelope) -> None:
        raise NotImplementedError


class LoggingNoteSaveHandler:
    envelope_type: EnvelopeType = NOTE_APPROVED

    async def handle(self, envelope: OutboxEnvelope) -> None:
        payload = NoteApprovedPayload.model_validate(envelope.payload)
        logger.info(
            "note approved: note_id=%s session_id=%s",
            payload.note_id,
            payload.session_id,
        )
