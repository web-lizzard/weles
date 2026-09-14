from collections.abc import Callable

from application.remember.dto import (
    DuePartitionDTO,
    NothingDueDTO,
    SittingOpenedDTO,
    SittingResumedDTO,
)
from application.remember.ports import Clock, UnitOfWork
from domain.remember.due_partition import partition_due
from domain.remember.ports import ReviewCatalog, Scheduler
from domain.remember.scheduling_state import due_card_ids
from domain.remember.sitting import Sitting
from domain.remember.value_objects import (
    MIN_RESUME_HORIZON,
    ResumeHorizon,
    ShowingLimit,
)
from domain.shared.identity.model import UserId


class OpenSittingCommand:
    def __init__(
        self,
        uow_factory: Callable[[UserId], UnitOfWork],
        catalog: ReviewCatalog,
        clock: Clock,
        showing_limit: ShowingLimit,
        scheduler: Scheduler,
        resume_horizon: ResumeHorizon | None = None,
    ) -> None:
        self._uow_factory: Callable[[UserId], UnitOfWork] = uow_factory
        self._catalog: ReviewCatalog = catalog
        self._clock: Clock = clock
        self._showing_limit: ShowingLimit = showing_limit
        self._scheduler: Scheduler = scheduler
        self._resume_horizon: ResumeHorizon = resume_horizon or ResumeHorizon(
            value=MIN_RESUME_HORIZON
        )

    async def handle(
        self, owner: UserId
    ) -> SittingOpenedDTO | SittingResumedDTO | NothingDueDTO:
        """Open one sitting over every card due at this instant, or write nothing.

        If the latest sitting is still offered and unfinished, return it without
        writing. Otherwise mint a new sitting over the due set, or nothing due.
        """
        as_of = self._clock.now()
        candidates = await self._catalog.list_reviewable(owner)
        live_stamp = self._scheduler.stamp()
        by_id = {card.id: card for card in candidates}

        async with self._uow_factory(owner) as uow:
            states = await uow.scheduling_states.get_many(tuple(by_id))

            latest = await uow.sittings.latest(owner)
            if latest is not None and latest.is_offered(as_of):
                present = latest.visible(frozenset(by_id))
                sitting_events = await uow.review_events.list_by_sitting(latest.id)
                if not latest.is_finished(present, sitting_events):
                    card_id = latest.next_card(present, sitting_events)
                    assert card_id is not None
                    reviewable = by_id[card_id]
                    sitting_complete = latest.is_finished(present, sitting_events)
                    outstanding_count = len(latest.outstanding(present, sitting_events))
                    due = DuePartitionDTO.from_domain(
                        partition_due(
                            frozenset(by_id),
                            states,
                            latest,
                            sitting_events,
                            as_of,
                            live_stamp,
                        )
                    )
                    return SittingResumedDTO(
                        sitting_id=latest.id.value,
                        card_id=card_id.value,
                        front=reviewable.front,
                        sitting_complete=sitting_complete,
                        outstanding_count=outstanding_count,
                        due=due,
                    )

            due = due_card_ids(frozenset(by_id), states, as_of, live_stamp)
            if not due:
                return NothingDueDTO()

            sitting = Sitting.open(
                owner, due, as_of, self._showing_limit, self._resume_horizon
            )
            present = sitting.visible(frozenset(by_id))
            card_id = sitting.next_card(present, events=[])

            if card_id is None:
                return NothingDueDTO()

            reviewable = by_id[card_id]
            sitting_complete = sitting.is_finished(present, events=[])
            outstanding_count = len(sitting.outstanding(present, events=[]))
            due_partition = DuePartitionDTO.from_domain(
                partition_due(
                    frozenset(by_id),
                    states,
                    sitting,
                    (),
                    as_of,
                    live_stamp,
                )
            )
            await uow.sittings.save(sitting)
            await uow.commit()

        return SittingOpenedDTO(
            sitting_id=sitting.id.value,
            card_id=card_id.value,
            front=reviewable.front,
            sitting_complete=sitting_complete,
            outstanding_count=outstanding_count,
            due=due_partition,
        )
