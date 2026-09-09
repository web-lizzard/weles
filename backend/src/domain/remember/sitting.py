# pyright: reportUnusedParameter=false
from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel, model_validator

from domain.remember.exceptions import EmptySittingError
from domain.remember.review_event import ReviewEvent
from domain.remember.value_objects import CardId, ShowingLimit, SittingId


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
        ...

    def is_finished(
        self,
        present: frozenset[CardId],
        events: Sequence[ReviewEvent],
    ) -> bool:
        """True when every present member is finished (Good+ or at showing_limit)."""
        ...

    def _eligible_pool(
        self,
        present: frozenset[CardId],
        events: Sequence[ReviewEvent],
    ) -> frozenset[CardId]:
        """Internal: present, unfinished, least shown. Uses self.showing_limit."""
        ...
