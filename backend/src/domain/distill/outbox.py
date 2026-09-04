from uuid import UUID

from pydantic import BaseModel

from domain.shared.outbox.model import EnvelopeType, OutboxEnvelope

NOTE_SAVED = EnvelopeType(name="note_saved")


class NoteSavedPayload(BaseModel, frozen=True):
    note_id: UUID

    def to_envelope(self) -> OutboxEnvelope:
        return OutboxEnvelope.pending(NOTE_SAVED, self.model_dump(mode="json"))
