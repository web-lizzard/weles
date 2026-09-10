from application.remember.dto import DueCountDTO, DuePartitionDTO
from application.remember.ports import Clock
from domain.remember.due_partition import partition_due
from domain.remember.ports import (
    ReviewCatalog,
    ReviewEventStore,
    Scheduler,
    SchedulingStateRepository,
    SittingRepository,
)


class DueCountQuery:
    def __init__(
        self,
        sittings: SittingRepository,
        events: ReviewEventStore,
        catalog: ReviewCatalog,
        scheduling_states: SchedulingStateRepository,
        clock: Clock,
        scheduler: Scheduler,
    ) -> None:
        self._sittings: SittingRepository = sittings
        self._events: ReviewEventStore = events
        self._catalog: ReviewCatalog = catalog
        self._scheduling_states: SchedulingStateRepository = scheduling_states
        self._clock: Clock = clock
        self._scheduler: Scheduler = scheduler

    async def handle(self) -> DueCountDTO:
        """Return how many cards are due and why. Read-only; never writes."""
        as_of = self._clock.now()
        reviewable = await self._catalog.list_reviewable()
        by_id = {card.id: card for card in reviewable}
        live_ids = frozenset(by_id)
        states = await self._scheduling_states.get_many(tuple(by_id))

        latest = await self._sittings.latest()
        sitting = latest if latest is not None and latest.is_offered(as_of) else None
        sitting_events = (
            await self._events.list_by_sitting(sitting.id)
            if sitting is not None
            else ()
        )

        partition = partition_due(
            live_ids,
            states,
            sitting,
            sitting_events,
            as_of,
            self._scheduler.stamp(),
        )
        return DueCountDTO(
            due=DuePartitionDTO(
                total=partition.total,
                not_yet_seen=partition.not_yet_seen,
                seen_still_owed=partition.seen_still_owed,
                ripe_outside_sitting=partition.ripe_outside_sitting,
            )
        )
