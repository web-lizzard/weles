# pyright: reportUnusedParameter=false
from collections.abc import Sequence
from typing import Protocol

from domain.remember.review_event import ReviewEvent
from domain.remember.value_objects import CardId, SittingId


class Draw(Protocol):
    """Picks one id from Sitting._eligible_pool. Not the ordering rule.

    Sitting.next_card always uses sitting_seeded_draw. Tests may build a
    Draw without going through Sitting.
    """

    def pick(self, pool: Sequence[CardId]) -> CardId: ...


def sitting_seeded_draw(sitting_id: SittingId, events: Sequence[ReviewEvent]) -> Draw:
    """Draw: same sitting id + events => same pick. No stored cursor."""
    ...
