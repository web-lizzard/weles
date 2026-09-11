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
        """Whole aggregate, including showing_limit and resume_horizon. Write-once."""
        ...

    async def get(self, sitting_id: SittingId) -> Sitting | None: ...

    async def latest(self) -> Sitting | None:
        """The sitting with the greatest opened_at, or None if none stored.

        Offer and finish are not this port's filter. Uniqueness at mint
        means this is the only sitting that can still be resumable.
        """
        ...


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
    """Rebuild a card's scheduling state from its review log.

    Folds Scheduler.review over stored events so a stale memoized record
    can be discarded and reconstructed at any time. Depends only on the
    Scheduler port; no concrete adapter is imported here.
    """

    def __init__(self, scheduler: Scheduler) -> None:
        self._scheduler: Scheduler = scheduler

    def replay(
        self, card_id: CardId, events: Sequence[ReviewEvent]
    ) -> SchedulingState | None:
        """Fold graded events in reviewed_at order; return None when none remain.

        Each scheduler result becomes the next previous state. Only
        card_id, reviewed_at, and a Grade outcome are read — sitting_id
        never reaches the scheduler.
        """
        graded: list[tuple[Grade, datetime]] = []
        for event in events:
            if event.card_id != card_id:
                continue
            outcome = event.outcome
            if isinstance(outcome, Grade):
                graded.append((outcome, event.reviewed_at))
        if not graded:
            return None

        ordered = sorted(graded, key=lambda item: item[1])
        previous: SchedulingState | None = None
        for grade, reviewed_at in ordered:
            previous = self._scheduler.review(
                previous,
                card_id,
                grade,
                reviewed_at,
            )
        return previous
