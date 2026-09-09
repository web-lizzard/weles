# pyright: reportUnusedParameter=false
from collections.abc import Callable

from application.remember.dto import NothingDueDTO, SittingOpenedDTO
from application.remember.ports import Clock, UnitOfWork
from domain.remember.ports import ReviewCatalog
from domain.remember.value_objects import ShowingLimit


class OpenSittingCommand:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        catalog: ReviewCatalog,
        clock: Clock,
        showing_limit: ShowingLimit,
    ) -> None:
        self._uow_factory: Callable[[], UnitOfWork] = uow_factory
        self._catalog: ReviewCatalog = catalog
        self._clock: Clock = clock
        self._showing_limit: ShowingLimit = showing_limit

    async def handle(self) -> SittingOpenedDTO | NothingDueDTO:
        """
        1. as_of = clock.now()
        2. candidates = catalog.list_reviewable()
        3. load memoized states for those ids (missing = never reviewed)
        4. due = {id | card_is_due(state, as_of)}
        5. if due is empty: return NothingDueDTO — no sitting
        6. Sitting.open(due, as_of, showing_limit); uow.sittings.save; commit
        7. present = sitting.visible(live)
        8. sitting.next_card(present, events=[]); return that front
        """
        ...
