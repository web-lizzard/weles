from application.remember.dto import PresentedCardDTO
from domain.remember.exceptions import CardNotReviewableError, SittingNotFoundError
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
        """Load the sitting and return the stable next draw. Read-only.

        Resume-slice contract (not wired as a separate path): also
        outstanding_count from sitting.outstanding. Does not evaluate
        is_offered — caller already holds the id.
        """
        sitting = await self._sittings.get(sitting_id)
        if sitting is None:
            raise SittingNotFoundError

        sitting_events = await self._events.list_by_sitting(sitting_id)
        reviewable = await self._catalog.list_reviewable()
        live = frozenset(card.id for card in reviewable)
        present = sitting.visible(live)
        card_id = sitting.next_card(present, sitting_events)
        sitting_complete = sitting.is_finished(present, sitting_events)
        outstanding_count = len(sitting.outstanding(present, sitting_events))
        if card_id is None:
            return PresentedCardDTO(
                sitting_id=sitting_id.value,
                card_id=None,
                front=None,
                sitting_complete=sitting_complete,
                outstanding_count=outstanding_count,
            )

        card = await self._catalog.get_reviewable(card_id)
        if card is None:
            raise CardNotReviewableError

        return PresentedCardDTO(
            sitting_id=sitting_id.value,
            card_id=card_id.value,
            front=card.front,
            sitting_complete=sitting_complete,
            outstanding_count=outstanding_count,
        )
