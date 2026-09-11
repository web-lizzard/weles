from collections.abc import Callable
from datetime import datetime

from application.distill.ports import UnitOfWork
from domain.distill.value_objects import CardId, DiscardReason


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
        _ = (card_id, reason, detail, discarded_at)
