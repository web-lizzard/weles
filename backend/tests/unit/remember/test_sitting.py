from datetime import UTC, datetime
from uuid import uuid4

import pytest

from domain.remember.exceptions import EmptySittingError
from domain.remember.review_event import ReviewEvent
from domain.remember.sitting import Sitting
from domain.remember.value_objects import CardId, Grade, ShowingLimit, SittingId


def _card_id() -> CardId:
    return CardId(value=uuid4())


def _open_sitting(*card_ids: CardId) -> Sitting:
    return Sitting.open(
        frozenset(card_ids),
        datetime.now(UTC),
        ShowingLimit(value=2),
    )


def test_a_sitting_with_no_cards_is_refused() -> None:
    with pytest.raises(EmptySittingError):
        _ = Sitting.open(frozenset(), datetime.now(UTC), ShowingLimit(value=2))


def test_contains_reports_whether_a_card_is_in_the_stored_set() -> None:
    member = _card_id()
    outsider = _card_id()
    sitting = _open_sitting(member)

    assert sitting.contains(member) is True
    assert sitting.contains(outsider) is False


def test_visible_is_the_intersection_and_leaves_the_stored_set_unchanged() -> None:
    kept = _card_id()
    discarded_elsewhere = _card_id()
    sitting = _open_sitting(kept, discarded_elsewhere)
    stored = sitting.card_ids

    present = sitting.visible(frozenset({kept}))

    assert present == frozenset({kept})
    assert sitting.card_ids == stored == frozenset({kept, discarded_elsewhere})


def test_the_next_card_is_the_undone_member_shown_fewest_times() -> None:
    shown = _card_id()
    unshown = _card_id()
    sitting = _open_sitting(shown, unshown)
    events = (
        ReviewEvent(
            card_id=shown,
            reviewed_at=datetime.now(UTC),
            grade=Grade.FORGOT,
            sitting_id=sitting.id,
        ),
    )

    assert sitting.next_card(frozenset({shown, unshown}), events) == unshown


def test_grades_from_another_sitting_do_not_finish_this_one_or_hide_its_next_card() -> (
    None
):
    first = _card_id()
    second = _card_id()
    sitting = _open_sitting(first, second)
    foreign = (
        ReviewEvent(
            card_id=first,
            reviewed_at=datetime.now(UTC),
            grade=Grade.GOOD,
            sitting_id=SittingId.new(),
        ),
        ReviewEvent(
            card_id=second,
            reviewed_at=datetime.now(UTC),
            grade=Grade.GOOD,
            sitting_id=SittingId.new(),
        ),
    )
    present = frozenset({first, second})

    assert sitting.is_finished(present, foreign) is False
    assert sitting.next_card(present, foreign) in present
