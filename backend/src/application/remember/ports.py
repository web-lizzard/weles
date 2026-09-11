from datetime import datetime
from typing import Protocol

from domain.remember.ports import (
    ReviewEventStore,
    SchedulingStateRepository,
    SittingRepository,
)
from domain.shared.outbox.ports import OutboxAppender


class Clock(Protocol):
    def now(self) -> datetime:
        """Timezone-aware UTC. opened_at, reviewed_at, and horizon as_of."""
        ...


class UnitOfWork(Protocol):
    sittings: SittingRepository
    review_events: ReviewEventStore
    scheduling_states: SchedulingStateRepository
    outbox: OutboxAppender

    async def __aenter__(self) -> "UnitOfWork": ...

    async def __aexit__(self, *exc: object) -> None: ...

    async def commit(self) -> None: ...
