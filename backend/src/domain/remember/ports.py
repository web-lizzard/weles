# pyright: reportUnusedParameter=false
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from pydantic import BaseModel

from domain.remember.review_event import ReviewEvent
from domain.remember.scheduling_state import SchedulingState
from domain.remember.sitting import Sitting
from domain.remember.value_objects import CardId, Grade, SchedulerStamp, SittingId


class ReviewableCard(BaseModel, frozen=True):
    id: CardId
    front: str
    back: str


class ReviewCatalog(Protocol):
    async def list_reviewable(self) -> Sequence[ReviewableCard]: ...

    async def get_reviewable(self, card_id: CardId) -> ReviewableCard | None: ...


class SittingRepository(Protocol):
    async def save(self, sitting: Sitting) -> None:
        """Whole aggregate, including showing_limit."""
        ...

    async def get(self, sitting_id: SittingId) -> Sitting | None: ...


class ReviewEventStore(Protocol):
    async def save(self, event: ReviewEvent) -> None: ...

    async def list_by_card(self, card_id: CardId) -> Sequence[ReviewEvent]:
        """Chronological by reviewed_at. Replay input."""
        ...

    async def list_by_sitting(self, sitting_id: SittingId) -> Sequence[ReviewEvent]: ...


class SchedulingStateRepository(Protocol):
    async def save(self, state: SchedulingState) -> None: ...

    async def get(self, card_id: CardId) -> SchedulingState | None: ...

    async def get_many(
        self, card_ids: Sequence[CardId]
    ) -> dict[CardId, SchedulingState]: ...


class Scheduler(Protocol):
    def stamp(self) -> SchedulerStamp: ...

    def review(
        self,
        previous: SchedulingState | None,
        card_id: CardId,
        grade: Grade,
        reviewed_at: datetime,
    ) -> SchedulingState: ...


class SchedulingReplay:
    def __init__(self, scheduler: Scheduler) -> None:
        self._scheduler: Scheduler = scheduler

    def replay(
        self, card_id: CardId, events: Sequence[ReviewEvent]
    ) -> SchedulingState | None: ...
