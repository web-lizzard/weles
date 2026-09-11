from collections.abc import Callable

from application.remember.dto import RevealedCardDTO
from application.remember.ports import Clock, UnitOfWork
from domain.remember.exceptions import (
    CardNotInSittingError,
    CardNotReviewableError,
    SittingExpiredError,
    SittingNotFoundError,
)
from domain.remember.ports import ReviewCatalog
from domain.remember.review_event import ReviewEvent
from domain.remember.value_objects import CardId, Reveal, SittingId


class RevealBackCommand:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        catalog: ReviewCatalog,
        clock: Clock,
    ) -> None:
        self._uow_factory: Callable[[], UnitOfWork] = uow_factory
        self._catalog: ReviewCatalog = catalog
        self._clock: Clock = clock

    async def handle(self, sitting_id: SittingId, card_id: CardId) -> RevealedCardDTO:
        """Record that the back was revealed and return front and back text."""
        async with self._uow_factory() as uow:
            sitting = await uow.sittings.get(sitting_id)
            if sitting is None:
                raise SittingNotFoundError
            if not sitting.is_offered(self._clock.now()):
                raise SittingExpiredError

            if not sitting.contains(card_id):
                raise CardNotInSittingError

            reviewable = await self._catalog.get_reviewable(card_id)
            if reviewable is None:
                raise CardNotReviewableError

            result = RevealedCardDTO(
                sitting_id=sitting_id.value,
                card_id=card_id.value,
                front=reviewable.front,
                back=reviewable.back,
            )

            sitting_events = await uow.review_events.list_by_sitting(sitting_id)
            already_revealed = any(
                event.card_id == card_id and isinstance(event.payload, Reveal)
                for event in sitting_events
            )
            if already_revealed:
                return result

            reviewed_at = self._clock.now()
            event = ReviewEvent(
                card_id=card_id,
                reviewed_at=reviewed_at,
                payload=Reveal(),
                sitting_id=sitting_id,
            )
            await uow.review_events.save(event)
            await uow.commit()

            return result
