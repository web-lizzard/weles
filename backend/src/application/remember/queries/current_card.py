from application.remember.dto import DuePartitionDTO, PresentedCardDTO
from application.remember.ports import Clock
from domain.remember.due_partition import partition_due
from domain.remember.exceptions import (
    CardNotReviewableError,
    SittingExpiredError,
    SittingNotFoundError,
)
from domain.remember.ports import (
    ReviewCatalog,
    ReviewEventReader,
    Scheduler,
    SchedulingStateReader,
    SittingReader,
)
from domain.remember.value_objects import SittingId


class CurrentCardQuery:
    def __init__(
        self,
        sittings: SittingReader,
        events: ReviewEventReader,
        catalog: ReviewCatalog,
        scheduling_states: SchedulingStateReader,
        clock: Clock,
        scheduler: Scheduler,
    ) -> None:
        self._sittings: SittingReader = sittings
        self._events: ReviewEventReader = events
        self._catalog: ReviewCatalog = catalog
        self._scheduling_states: SchedulingStateReader = scheduling_states
        self._clock: Clock = clock
        self._scheduler: Scheduler = scheduler

    async def handle(self, sitting_id: SittingId) -> PresentedCardDTO:
        """Load the sitting and return the stable next draw. Read-only.

        Refuses sittings past their resume horizon. Also returns
        outstanding_count from sitting.outstanding.
        """
        sitting = await self._sittings.get(sitting_id)
        if sitting is None:
            raise SittingNotFoundError
        as_of = self._clock.now()
        if not sitting.is_offered(as_of):
            raise SittingExpiredError

        sitting_events = await self._events.list_by_sitting(sitting_id)
        reviewable = await self._catalog.list_reviewable()
        by_id = {card.id: card for card in reviewable}
        live = frozenset(by_id)
        states = await self._scheduling_states.get_many(tuple(by_id))
        present = sitting.visible(live)
        card_id = sitting.next_card(present, sitting_events)
        sitting_complete = sitting.is_finished(present, sitting_events)
        outstanding_count = len(sitting.outstanding(present, sitting_events))
        due = DuePartitionDTO.from_domain(
            partition_due(
                live,
                states,
                sitting,
                sitting_events,
                as_of,
                self._scheduler.stamp(),
            )
        )
        if card_id is None:
            return PresentedCardDTO(
                sitting_id=sitting_id.value,
                card_id=None,
                front=None,
                sitting_complete=sitting_complete,
                outstanding_count=outstanding_count,
                due=due,
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
            due=due,
        )
