from datetime import UTC, datetime
from uuid import uuid4

from domain.remember.review_event import ReviewEvent
from domain.remember.sitting_completion import SittingCompletion
from domain.remember.value_objects import CardId, Grade, ShowingLimit, SittingId


def _card_id() -> CardId:
    return CardId(value=uuid4())


def _event(
    card_id: CardId,
    sitting_id: SittingId,
    grade: Grade,
) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,
        reviewed_at=datetime.now(UTC),
        grade=grade,
        sitting_id=sitting_id,
    )


def test_only_good_and_easy_grades_finish_a_card() -> None:
    assert SittingCompletion.grade_finishes_card(Grade.GOOD) is True
    assert SittingCompletion.grade_finishes_card(Grade.EASY) is True
    assert SittingCompletion.grade_finishes_card(Grade.FORGOT) is False
    assert SittingCompletion.grade_finishes_card(Grade.HARD) is False


def test_a_good_grade_finishes_the_card_even_when_it_has_been_shown_once() -> None:
    card = _card_id()
    sitting_id = SittingId.new()
    completion = SittingCompletion(
        (_event(card, sitting_id, Grade.GOOD),),
        ShowingLimit(value=2),
    )

    assert completion.card_is_finished(card) is True


def test_a_card_shown_the_limit_times_is_finished_without_a_good_grade() -> None:
    card = _card_id()
    sitting_id = SittingId.new()
    completion = SittingCompletion(
        (
            _event(card, sitting_id, Grade.FORGOT),
            _event(card, sitting_id, Grade.HARD),
        ),
        ShowingLimit(value=2),
    )

    assert completion.showing_count(card) == 2
    assert completion.card_is_finished(card) is True


def test_discarded_members_do_not_keep_a_sitting_open() -> None:
    present_card = _card_id()
    discarded = _card_id()
    sitting_id = SittingId.new()
    completion = SittingCompletion(
        (_event(present_card, sitting_id, Grade.GOOD),),
        ShowingLimit(value=2),
    )

    assert (
        completion.sitting_is_finished(
            frozenset({present_card, discarded}),
            frozenset({present_card}),
        )
        is True
    )
