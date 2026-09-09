# pyright: reportUnusedParameter=false
from collections.abc import Sequence

from domain.remember.review_event import ReviewEvent
from domain.remember.value_objects import CardId, Grade, ShowingLimit


class SittingCompletion:
    """Whether a card or the sitting is finished here. Reads grades, never due_at."""

    def __init__(self, events: Sequence[ReviewEvent], limit: ShowingLimit) -> None: ...

    def showing_count(self, card_id: CardId) -> int: ...

    def card_is_finished(self, card_id: CardId) -> bool: ...

    def sitting_is_finished(
        self, membership: frozenset[CardId], present: frozenset[CardId]
    ) -> bool: ...

    @staticmethod
    def grade_finishes_card(grade: Grade) -> bool: ...
