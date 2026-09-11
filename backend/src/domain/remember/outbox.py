from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from domain.shared.outbox.model import EnvelopeType, OutboxEnvelope

CARD_REJECTED = EnvelopeType(name="card_rejected")


class CardRejectedPayload(BaseModel, frozen=True):
    card_id: UUID
    rejected_at: datetime

    def to_envelope(self) -> OutboxEnvelope:
        return OutboxEnvelope.pending(CARD_REJECTED, self.model_dump(mode="json"))
