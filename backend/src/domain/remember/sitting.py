import hashlib
import random
from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel, model_validator

from domain.remember.exceptions import EmptySittingError
from domain.remember.review_event import ReviewEvent
from domain.remember.value_objects import (
    FINISHING_GRADES,
    CardId,
    ShowingLimit,
    SittingId,
)


class Sitting(BaseModel, frozen=True):
    id: SittingId
    card_ids: frozenset[CardId]
    opened_at: datetime
    showing_limit: ShowingLimit
    """Snapshotted at open. Repository round-trips it; later commands never read env."""

    @model_validator(mode="after")
    def _validate_intent(self) -> "Sitting":
        """Refuse an empty card_ids set (EmptySittingError)."""
        if not self.card_ids:
            raise EmptySittingError
        return self

    @classmethod
    def open(
        cls,
        card_ids: frozenset[CardId],
        opened_at: datetime,
        showing_limit: ShowingLimit,
    ) -> "Sitting":
        return cls(
            id=SittingId.new(),
            card_ids=card_ids,
            opened_at=opened_at,
            showing_limit=showing_limit,
        )

    def contains(self, card_id: CardId) -> bool:
        return card_id in self.card_ids

    def visible(self, live: frozenset[CardId]) -> frozenset[CardId]:
        """Membership as read: gone ids drop out; the stored set is unchanged."""
        return self.card_ids & live

    def next_card(
        self,
        present: frozenset[CardId],
        events: Sequence[ReviewEvent],
    ) -> CardId | None:
        """One card from _eligible_pool, seeded from self.id + events. None if empty."""
        pool = self._eligible_pool(present, events)
        if not pool:
            return None
        ordered = sorted(pool, key=lambda card_id: card_id.value)
        return self._seeded_pick(events, ordered)

    def is_finished(
        self,
        present: frozenset[CardId],
        events: Sequence[ReviewEvent],
    ) -> bool:
        """True when every present member is finished (Good+ or at showing_limit)."""
        sitting_events = self._sitting_events(events)
        return all(
            self._card_is_finished(card_id, sitting_events) for card_id in present
        )

    def _eligible_pool(
        self,
        present: frozenset[CardId],
        events: Sequence[ReviewEvent],
    ) -> frozenset[CardId]:
        """Internal: present, unfinished, least shown. Uses self.showing_limit."""
        sitting_events = self._sitting_events(events)
        unfinished = {
            card_id
            for card_id in present
            if not self._card_is_finished(card_id, sitting_events)
        }
        if not unfinished:
            return frozenset()
        counts = {
            card_id: self._showing_count(card_id, sitting_events)
            for card_id in unfinished
        }
        minimum = min(counts.values())
        return frozenset(
            card_id for card_id, count in counts.items() if count == minimum
        )

    def _sitting_events(self, events: Sequence[ReviewEvent]) -> tuple[ReviewEvent, ...]:
        return tuple(event for event in events if event.sitting_id == self.id)

    def _showing_count(self, card_id: CardId, events: Sequence[ReviewEvent]) -> int:
        return sum(1 for event in events if event.card_id == card_id)

    def _card_is_finished(self, card_id: CardId, events: Sequence[ReviewEvent]) -> bool:
        if any(
            event.card_id == card_id and event.grade in FINISHING_GRADES
            for event in events
        ):
            return True
        return self._showing_count(card_id, events) >= self.showing_limit.value

    def _seeded_pick(
        self, events: Sequence[ReviewEvent], pool: Sequence[CardId]
    ) -> CardId:
        rng = random.Random(self._draw_seed(events))
        return pool[rng.randrange(len(pool))]

    def _draw_seed(self, events: Sequence[ReviewEvent]) -> int:
        parts = [str(self.id.value)]
        ordered = sorted(
            self._sitting_events(events),
            key=lambda event: (
                event.reviewed_at,
                event.card_id.value,
                event.grade,
                event.sitting_id.value,
            ),
        )
        for event in ordered:
            parts.extend(
                (
                    str(event.card_id.value),
                    event.reviewed_at.isoformat(),
                    event.grade,
                    str(event.sitting_id.value),
                )
            )
        digest = hashlib.sha256("|".join(parts).encode()).digest()
        return int.from_bytes(digest[:8], "big")
