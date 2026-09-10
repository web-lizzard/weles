import asyncio

from adapters.out.in_memory.remember.review_event_store import InMemoryReviewEventStore
from adapters.out.in_memory.remember.scheduling_state_repository import (
    InMemorySchedulingStateRepository,
)
from adapters.out.in_memory.remember.sitting_repository import InMemorySittingRepository
from domain.remember.review_event import ReviewEvent
from domain.remember.scheduling_state import SchedulingState
from domain.remember.sitting import Sitting
from domain.remember.value_objects import CardId, SittingId


class InMemoryUnitOfWork:
    sittings: InMemorySittingRepository
    review_events: InMemoryReviewEventStore
    scheduling_states: InMemorySchedulingStateRepository

    def __init__(
        self,
        sittings: InMemorySittingRepository,
        review_events: InMemoryReviewEventStore,
        scheduling_states: InMemorySchedulingStateRepository,
        lock: asyncio.Lock,
    ) -> None:
        self.sittings = sittings
        self.review_events = review_events
        self.scheduling_states = scheduling_states
        self._lock: asyncio.Lock = lock
        self._committed: bool = False
        self._sittings_snapshot: dict[SittingId, Sitting] = {}
        self._review_events_snapshot: list[ReviewEvent] = []
        self._scheduling_states_snapshot: dict[CardId, SchedulingState] = {}

    async def __aenter__(self) -> "InMemoryUnitOfWork":
        _ = await self._lock.acquire()
        self._committed = False
        self._sittings_snapshot = self.sittings.snapshot()
        self._review_events_snapshot = self.review_events.snapshot()
        self._scheduling_states_snapshot = self.scheduling_states.snapshot()
        return self

    async def __aexit__(self, *exc: object) -> None:
        try:
            if not self._committed:
                self.sittings.restore(self._sittings_snapshot)
                self.review_events.restore(self._review_events_snapshot)
                self.scheduling_states.restore(self._scheduling_states_snapshot)
        finally:
            self._lock.release()

    async def commit(self) -> None:
        self._committed = True
