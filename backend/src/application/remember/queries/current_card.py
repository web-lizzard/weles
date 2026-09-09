# pyright: reportUnusedParameter=false
from application.remember.dto import PresentedCardDTO
from domain.remember.ports import ReviewCatalog, ReviewEventStore, SittingRepository
from domain.remember.value_objects import SittingId


class CurrentCardQuery:
    def __init__(
        self,
        sittings: SittingRepository,
        events: ReviewEventStore,
        catalog: ReviewCatalog,
    ) -> None:
        self._sittings: SittingRepository = sittings
        self._events: ReviewEventStore = events
        self._catalog: ReviewCatalog = catalog

    async def handle(self, sitting_id: SittingId) -> PresentedCardDTO:
        """
        No UnitOfWork. Load sitting, events, present = sitting.visible(live).
        sitting.next_card so presentation is stable across requests.
        ShowingLimit is on the sitting.
        """
        ...
