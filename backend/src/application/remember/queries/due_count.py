from application.remember.dto import DueCountDTO
from application.remember.ports import Clock
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
        """Return how many cards are due. Read-only; zeros until Phase 5."""
        return DueCountDTO()
