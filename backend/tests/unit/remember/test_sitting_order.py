from datetime import UTC, datetime
from uuid import uuid4

from domain.remember.review_event import ReviewEvent
from domain.remember.sitting_order import sitting_seeded_draw
from domain.remember.value_objects import CardId, Grade, SittingId


def _card_id() -> CardId:
    return CardId(value=uuid4())


def test_the_same_sitting_and_events_draw_the_same_card_from_the_same_pool() -> None:
    sitting_id = SittingId.new()
    pool = (_card_id(), _card_id())
    events = (
        ReviewEvent(
            card_id=pool[0],
            reviewed_at=datetime.now(UTC),
            grade=Grade.FORGOT,
            sitting_id=sitting_id,
        ),
    )

    draw = sitting_seeded_draw(sitting_id, events)

    assert draw is not None
    first = draw.pick(pool)
    second = sitting_seeded_draw(sitting_id, events).pick(pool)
    assert first == second
    assert first in pool
