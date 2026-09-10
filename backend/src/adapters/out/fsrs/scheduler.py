import hashlib
import random
from datetime import UTC, datetime
from typing import cast

import fsrs
from domain.remember.scheduling_state import SchedulingState
from domain.remember.value_objects import (
    CardId,
    Grade,
    OpaqueSchedulerState,
    SchedulerAlgorithm,
    SchedulerStamp,
)
from fsrs.card import CardDict

PARAMETER_VERSION = "fsrs-6.3.2-defaults"

_RATINGS: dict[Grade, fsrs.Rating] = {
    Grade.FORGOT: fsrs.Rating.Again,
    Grade.HARD: fsrs.Rating.Hard,
    Grade.GOOD: fsrs.Rating.Good,
    Grade.EASY: fsrs.Rating.Easy,
}


class FsrsScheduler:
    """The only code that speaks the scheduling library's vocabulary.

    The domain gets an indexable due_at and a blob it never reads.
    """

    def __init__(self) -> None:
        self._scheduler: fsrs.Scheduler = fsrs.Scheduler()

    def stamp(self) -> SchedulerStamp:
        return SchedulerStamp(
            algorithm=SchedulerAlgorithm.FSRS,
            parameter_version=PARAMETER_VERSION,
        )

    def review(
        self,
        previous: SchedulingState | None,
        card_id: CardId,
        grade: Grade,
        reviewed_at: datetime,
    ) -> SchedulingState:
        card = fsrs.Card() if previous is None else _restore(previous)
        reviewed = self._review_card(card, _RATINGS[grade], card_id, grade, reviewed_at)
        return SchedulingState(
            card_id=card_id,
            due_at=reviewed.due,
            scheduler_state=OpaqueSchedulerState(payload=dict(reviewed.to_dict())),
            stamp=self.stamp(),
        )

    def _review_card(
        self,
        card: fsrs.Card,
        rating: fsrs.Rating,
        card_id: CardId,
        grade: Grade,
        reviewed_at: datetime,
    ) -> fsrs.Card:
        """Draw the library's interval fuzz from this event's own facts.

        The library fuzzes through the global random generator, so the seed
        is set around the call and the caller's generator state restored
        after it. The region holds no await, which makes it atomic against
        the event loop — this assumes the port is driven from the loop
        thread, never from an executor.
        """
        state = random.getstate()
        random.seed(_fuzz_seed(card_id, grade, reviewed_at))
        try:
            reviewed, _ = self._scheduler.review_card(
                card, rating, review_datetime=reviewed_at.astimezone(UTC)
            )
        finally:
            random.setstate(state)
        return reviewed


def _fuzz_seed(card_id: CardId, grade: Grade, reviewed_at: datetime) -> int:
    """Derived, never stored — the same event always draws the same fuzz.

    Digested rather than hashed, because hash() over str is salted per
    process and a replay runs in a later one.
    """
    parts = (str(card_id.value), reviewed_at.isoformat(), grade.value)
    digest = hashlib.sha256("|".join(parts).encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _restore(previous: SchedulingState) -> fsrs.Card:
    """The blob the domain carries around is this library's own card dict."""
    payload = cast(object, previous.scheduler_state.payload)
    return fsrs.Card.from_dict(cast(CardDict, payload))
