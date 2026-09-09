from collections.abc import Callable

from application.remember.dto import NothingDueDTO, SittingOpenedDTO
from application.remember.ports import Clock, UnitOfWork
from domain.remember.ports import ReviewCatalog, Scheduler
from domain.remember.scheduling_state import card_is_due
from domain.remember.sitting import Sitting
from domain.remember.value_objects import ShowingLimit


class OpenSittingCommand:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        catalog: ReviewCatalog,
        clock: Clock,
        showing_limit: ShowingLimit,
        scheduler: Scheduler,
    ) -> None:
        self._uow_factory: Callable[[], UnitOfWork] = uow_factory
        self._catalog: ReviewCatalog = catalog
        self._clock: Clock = clock
        self._showing_limit: ShowingLimit = showing_limit
        self._scheduler: Scheduler = scheduler

    async def handle(self) -> SittingOpenedDTO | NothingDueDTO:
        """Open one sitting over every card due at this instant, or write nothing.

        Captures the clock once. A card is due when it has never been reviewed,
        its memoized stamp does not match the live scheduler, or its due_at has
        been reached. An empty due set returns NothingDueDTO without saving a
        sitting. Otherwise the sitting is committed in one unit of work and the
        first front is drawn from an empty review log.
        """
        as_of = self._clock.now()
        candidates = await self._catalog.list_reviewable()
        live_stamp = self._scheduler.stamp()
        by_id = {card.id: card for card in candidates}

        async with self._uow_factory() as uow:
            states = await uow.scheduling_states.get_many(tuple(by_id))
            due = frozenset(
                card_id
                for card_id in by_id
                if card_is_due(states.get(card_id), as_of, live_stamp)
            )
            if not due:
                return NothingDueDTO()

            sitting = Sitting.open(due, as_of, self._showing_limit)
            present = sitting.visible(frozenset(by_id))
            card_id = sitting.next_card(present, events=[])
            assert card_id is not None
            reviewable = by_id[card_id]
            sitting_complete = sitting.is_finished(present, events=[])
            await uow.sittings.save(sitting)
            await uow.commit()

        return SittingOpenedDTO(
            sitting_id=sitting.id.value,
            card_id=card_id.value,
            front=reviewable.front,
            sitting_complete=sitting_complete,
        )
