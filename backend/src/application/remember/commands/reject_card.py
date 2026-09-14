from collections.abc import Callable

from application.remember.ports import Clock, UnitOfWork
from domain.remember.exceptions import SittingNotFoundError
from domain.remember.outbox import CardRejectedPayload
from domain.remember.ports import ReviewableCard, ReviewCatalog
from domain.remember.review_event import ReviewEvent
from domain.remember.sitting import Sitting
from domain.remember.value_objects import CardId, Rejection, SittingId
from domain.shared.identity.model import UserId


class RejectCardCommand:
    def __init__(
        self,
        uow_factory: Callable[[UserId], UnitOfWork],
        catalog: ReviewCatalog,
        clock: Clock,
    ) -> None:
        self._uow_factory: Callable[[UserId], UnitOfWork] = uow_factory
        self._catalog: ReviewCatalog = catalog
        self._clock: Clock = clock

    async def handle(
        self, owner: UserId, sitting_id: SittingId, card_id: CardId
    ) -> None:
        async with self._uow_factory(owner) as uow:
            sitting = await self._require_sitting(uow, sitting_id, owner)
            sitting_events = await uow.review_events.list_by_sitting(sitting_id)
            by_id = await self._reviewable_by_id(owner)
            present = sitting.visible(frozenset(by_id))
            reviewed_at = self._clock.now()
            sitting.guard_outcome(card_id, present, sitting_events, reviewed_at)
            event = ReviewEvent(
                card_id=card_id,
                reviewed_at=reviewed_at,
                payload=Rejection(),
                sitting_id=sitting_id,
            )
            envelope = CardRejectedPayload(
                card_id=card_id.value, rejected_at=reviewed_at
            ).to_envelope()
            await uow.review_events.save(event)
            await uow.outbox.append(envelope)
            await uow.commit()

    async def _require_sitting(
        self, uow: UnitOfWork, sitting_id: SittingId, owner: UserId
    ) -> Sitting:
        sitting = await uow.sittings.get(sitting_id)
        if sitting is None or sitting.owner_id != owner:
            raise SittingNotFoundError
        return sitting

    async def _reviewable_by_id(self, owner: UserId) -> dict[CardId, ReviewableCard]:
        reviewable = await self._catalog.list_reviewable(owner)
        return {card.id: card for card in reviewable}
