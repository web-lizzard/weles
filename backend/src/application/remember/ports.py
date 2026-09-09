from datetime import datetime
from typing import Protocol

from domain.remember.ports import (
    ReviewEventStore,
    SchedulingStateRepository,
    SittingRepository,
)


class Clock(Protocol):
    def now(self) -> datetime:
        """Timezone-aware UTC. The only source of reviewed_at and opened_at."""
        ...


class UnitOfWork(Protocol):
    sittings: SittingRepository
    review_events: ReviewEventStore
    scheduling_states: SchedulingStateRepository

    async def __aenter__(self) -> "UnitOfWork": ...

    async def __aexit__(self, *exc: object) -> None: ...

    async def commit(self) -> None: ...
