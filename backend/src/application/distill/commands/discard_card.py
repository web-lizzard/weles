import logging
from collections.abc import Callable
from datetime import datetime

from application.distill.ports import UnitOfWork
from domain.distill.value_objects import CardId, Discard, DiscardReason

logger = logging.getLogger(__name__)


class DiscardCardCommand:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory: Callable[[], UnitOfWork] = uow_factory

    async def handle(
        self,
        card_id: CardId,
        reason: DiscardReason,
        detail: str | None,
        discarded_at: datetime,
    ) -> None:
        async with self._uow_factory() as uow:
            card = await uow.cards.get(card_id)
            if card is None:
                logger.info("card %s not found, skipping as no-op", card_id.value)
                return
            if card.discard is not None:
                logger.info("card %s redelivered, skipping as no-op", card_id.value)
                return

            card.discard = Discard(
                reason=reason,
                detail=detail,
                discarded_at=discarded_at,
            )
            await uow.cards.save(card)
            await uow.commit()
