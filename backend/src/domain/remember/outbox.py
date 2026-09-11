from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from domain.shared.outbox.model import EnvelopeType, OutboxEnvelope

CARD_REJECTED = EnvelopeType(name="card_rejected")


class CardRejectedPayload(BaseModel, frozen=True):
    card_id: UUID
    rejected_at: datetime

    def to_envelope(self) -> OutboxEnvelope:
        payload = self.model_dump(mode="json")
        payload["rejected_at"] = self.rejected_at.isoformat()
        return OutboxEnvelope.pending(CARD_REJECTED, payload)
