from application.remember.dto import RevealedCardDTO
from application.remember.ports import Clock
from domain.remember.exceptions import (
    CardNotInSittingError,
    CardNotReviewableError,
    SittingExpiredError,
    SittingNotFoundError,
)
from domain.remember.ports import ReviewCatalog, SittingRepository
from domain.remember.value_objects import CardId, SittingId


class RevealBackQuery:
    def __init__(
        self,
        sittings: SittingRepository,
        catalog: ReviewCatalog,
        clock: Clock,
    ) -> None:
        self._sittings: SittingRepository = sittings
        self._catalog: ReviewCatalog = catalog
        self._clock: Clock = clock

    async def handle(self, sitting_id: SittingId, card_id: CardId) -> RevealedCardDTO:
        """Return front and back for a sitting member. Read-only; no UnitOfWork."""
        sitting = await self._sittings.get(sitting_id)
        if sitting is None:
            raise SittingNotFoundError
        if not sitting.is_offered(self._clock.now()):
            raise SittingExpiredError

        if not sitting.contains(card_id):
            raise CardNotInSittingError

        reviewable = await self._catalog.get_reviewable(card_id)
        if reviewable is None:
            raise CardNotReviewableError

        return RevealedCardDTO(
            sitting_id=sitting_id.value,
            card_id=card_id.value,
            front=reviewable.front,
            back=reviewable.back,
        )
