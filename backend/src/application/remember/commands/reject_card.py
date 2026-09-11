from collections.abc import Callable

from application.remember.ports import Clock, UnitOfWork
from domain.remember.ports import ReviewCatalog
from domain.remember.value_objects import CardId, SittingId


class RejectCardCommand:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        catalog: ReviewCatalog,
        clock: Clock,
    ) -> None:
        self._uow_factory: Callable[[], UnitOfWork] = uow_factory
        self._catalog: ReviewCatalog = catalog
        self._clock: Clock = clock

    async def handle(self, sitting_id: SittingId, card_id: CardId) -> None:
        del sitting_id, card_id
