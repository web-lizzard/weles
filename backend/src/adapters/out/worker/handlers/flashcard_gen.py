import logging

from pydantic import ValidationError

from adapters.out.llm.tracing import observation
from application.distill.commands.generate_cards import GenerateCardsCommand
from domain.distill.outbox import NOTE_SAVED, NoteSavedPayload
from domain.distill.value_objects import NoteId
from domain.shared.outbox.model import EnvelopeType, OutboxEnvelope

logger = logging.getLogger(__name__)


class FlashcardGenHandler:
    envelope_type: EnvelopeType = NOTE_SAVED

    def __init__(self, command: GenerateCardsCommand) -> None:
        self._command: GenerateCardsCommand = command

    async def handle(self, envelope: OutboxEnvelope) -> None:
        try:
            payload = NoteSavedPayload.model_validate(envelope.payload)
        except ValidationError:
            logger.exception("malformed note_saved envelope: id=%s", envelope.id)
            return

        note_id = payload.note_id
        with observation(
            "distill_run",
            observation_type="chain",
            input_value={"note_id": str(note_id)},
            session_id=str(note_id),
        ):
            await self._command.handle(NoteId(value=note_id))
