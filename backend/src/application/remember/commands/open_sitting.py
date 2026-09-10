from collections.abc import Callable

from application.remember.dto import (
    NothingDueDTO,
    SittingOpenedDTO,
    SittingResumedDTO,
)
from application.remember.ports import Clock, UnitOfWork
from domain.remember.ports import ReviewCatalog, Scheduler
from domain.remember.scheduling_state import card_is_due
from domain.remember.sitting import Sitting
from domain.remember.value_objects import (
    MIN_RESUME_HORIZON,
    ResumeHorizon,
    ShowingLimit,
)


class OpenSittingCommand:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        catalog: ReviewCatalog,
        clock: Clock,
        showing_limit: ShowingLimit,
        scheduler: Scheduler,
        resume_horizon: ResumeHorizon | None = None,
    ) -> None:
        self._uow_factory: Callable[[], UnitOfWork] = uow_factory
        self._catalog: ReviewCatalog = catalog
        self._clock: Clock = clock
        self._showing_limit: ShowingLimit = showing_limit
        self._scheduler: Scheduler = scheduler
        self._resume_horizon: ResumeHorizon = resume_horizon or ResumeHorizon(
            value=MIN_RESUME_HORIZON
        )

    async def handle(self) -> SittingOpenedDTO | SittingResumedDTO | NothingDueDTO:
        """Open one sitting over every card due at this instant, or write nothing.

        Resume-slice contract (not replacing this body yet):

        1. sittings.latest() inside the unit of work.
        2. If present: is_offered(as_of), visible(live catalog) + events.
           Resumable iff offered and not is_finished.
        3. Resumable: return SittingResumedDTO (kind=resumed, outstanding_count
           from sitting.outstanding, next front from next_card). No save.
        4. Else: this mint path — due set empty → NothingDueDTO; else
           Sitting.open(..., resume_horizon=self._resume_horizon).

        Live path below is still mint-only (S-01).
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

            sitting = Sitting.open(
                due, as_of, self._showing_limit, self._resume_horizon
            )
            present = sitting.visible(frozenset(by_id))
            card_id = sitting.next_card(present, events=[])
            assert card_id is not None
            reviewable = by_id[card_id]
            sitting_complete = sitting.is_finished(present, events=[])
            outstanding_count = len(sitting.outstanding(present, events=[]))
            await uow.sittings.save(sitting)
            await uow.commit()

        return SittingOpenedDTO(
            sitting_id=sitting.id.value,
            card_id=card_id.value,
            front=reviewable.front,
            sitting_complete=sitting_complete,
            outstanding_count=outstanding_count,
        )
