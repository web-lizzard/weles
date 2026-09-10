# pyright: reportUnusedParameter=false
import asyncio

from adapters.out.in_memory.remember.review_event_store import InMemoryReviewEventStore
from adapters.out.in_memory.remember.scheduling_state_repository import (
    InMemorySchedulingStateRepository,
)
from adapters.out.in_memory.remember.sitting_repository import InMemorySittingRepository


class InMemoryUnitOfWork:
    def __init__(
        self,
        sittings: InMemorySittingRepository,
        review_events: InMemoryReviewEventStore,
        scheduling_states: InMemorySchedulingStateRepository,
        lock: asyncio.Lock,
    ) -> None: ...

    async def __aenter__(self) -> "InMemoryUnitOfWork": ...

    async def __aexit__(self, *exc: object) -> None: ...

    async def commit(self) -> None: ...
