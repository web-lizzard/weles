import logging

from pydantic import ValidationError

from application.distill.commands.discard_card import DiscardCardCommand
from domain.distill.value_objects import CardId, DiscardReason
from domain.remember.outbox import CARD_REJECTED, CardRejectedPayload
from domain.shared.outbox.model import EnvelopeType, OutboxEnvelope

logger = logging.getLogger(__name__)


class CardDiscardHandler:
    envelope_type: EnvelopeType = CARD_REJECTED

    def __init__(self, command: DiscardCardCommand) -> None:
        self._command: DiscardCardCommand = command

    async def handle(self, envelope: OutboxEnvelope) -> None:
        try:
            payload = CardRejectedPayload.model_validate(envelope.payload)
        except ValidationError:
            logger.exception("malformed card_rejected envelope: id=%s", envelope.id)
            return

        await self._command.handle(
            card_id=CardId(value=payload.card_id),
            reason=DiscardReason.USER_AUDIT,
            detail=None,
            discarded_at=payload.rejected_at,
        )
