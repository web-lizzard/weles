import logging

from pydantic import ValidationError

from application.distill.commands.save_note import SaveNoteCommand
from domain.capture.outbox import NOTE_APPROVED, NoteApprovedPayload
from domain.distill.value_objects import (
    NoteContent,
    NoteId,
    SessionId,
    TagSnapshot,
    TopicSnapshot,
)
from domain.shared.identity.model import UserId
from domain.shared.outbox.model import EnvelopeType, OutboxEnvelope

logger = logging.getLogger(__name__)


class SaveNoteHandler:
    envelope_type: EnvelopeType = NOTE_APPROVED

    def __init__(self, command: SaveNoteCommand) -> None:
        self._command: SaveNoteCommand = command

    async def handle(self, envelope: OutboxEnvelope) -> None:
        try:
            payload = NoteApprovedPayload.model_validate(envelope.payload)
        except ValidationError:
            logger.exception("malformed note_approved envelope: id=%s", envelope.id)
            return

        await self._command.handle(
            owner_id=UserId(value=payload.owner_id),
            note_id=NoteId(value=payload.note_id),
            session_id=SessionId(value=payload.session_id),
            topic=TopicSnapshot(id=payload.topic.id, label=payload.topic.label),
            content=NoteContent(value=payload.content),
            tags=[TagSnapshot(id=tag.id, label=tag.label) for tag in payload.tags],
            approved_at=payload.approved_at,
        )
