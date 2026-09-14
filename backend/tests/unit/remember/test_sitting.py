import hashlib
import random
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from domain.remember.exceptions import EmptySittingError
from domain.remember.review_event import ReviewEvent
from domain.remember.sitting import Sitting
from domain.remember.value_objects import (
    CardId,
    Grade,
    Graded,
    Rejection,
    ResumeHorizon,
    Reveal,
    ShowingLimit,
    SittingId,
)
from domain.shared.identity.model import UserId

_OWNER = UserId.new()


def _card_id() -> CardId:
    return CardId(value=uuid4())


def _open_sitting(*card_ids: CardId) -> Sitting:
    return Sitting.open(
        _OWNER,
        frozenset(card_ids),
        datetime.now(UTC),
        ShowingLimit(value=2),
    )


def _event(
    card_id: CardId,
    sitting_id: SittingId,
    grade: Grade,
) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,
        reviewed_at=datetime.now(UTC),
        payload=Graded(grade=grade),
        sitting_id=sitting_id,
    )


def _rejection(card_id: CardId, sitting_id: SittingId) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,
        reviewed_at=datetime.now(UTC),
        payload=Rejection(),
        sitting_id=sitting_id,
    )


def _reveal(card_id: CardId, sitting_id: SittingId) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,
        reviewed_at=datetime.now(UTC),
        payload=Reveal(),
        sitting_id=sitting_id,
    )


def test_a_sitting_with_no_cards_is_refused() -> None:
    with pytest.raises(EmptySittingError):
        _ = Sitting.open(_OWNER, frozenset(), datetime.now(UTC), ShowingLimit(value=2))


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
    events = (_event(shown, sitting.id, Grade.FORGOT),)

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
            payload=Graded(grade=Grade.GOOD),
            sitting_id=SittingId.new(),
        ),
        ReviewEvent(
            card_id=second,
            reviewed_at=datetime.now(UTC),
            payload=Graded(grade=Grade.GOOD),
            sitting_id=SittingId.new(),
        ),
    )
    present = frozenset({first, second})

    assert sitting.is_finished(present, foreign) is False
    assert sitting.next_card(present, foreign) in present


def test_a_good_grade_finishes_the_sitting() -> None:
    card = _card_id()
    sitting = _open_sitting(card)
    events = (_event(card, sitting.id, Grade.GOOD),)

    assert sitting.is_finished(frozenset({card}), events) is True


def test_an_easy_grade_finishes_the_sitting() -> None:
    card = _card_id()
    sitting = _open_sitting(card)
    events = (_event(card, sitting.id, Grade.EASY),)

    assert sitting.is_finished(frozenset({card}), events) is True


def test_a_forgot_grade_does_not_finish_the_sitting_on_its_own() -> None:
    card = _card_id()
    sitting = _open_sitting(card)
    events = (_event(card, sitting.id, Grade.FORGOT),)

    assert sitting.is_finished(frozenset({card}), events) is False


def test_a_hard_grade_does_not_finish_the_sitting_on_its_own() -> None:
    card = _card_id()
    sitting = _open_sitting(card)
    events = (_event(card, sitting.id, Grade.HARD),)

    assert sitting.is_finished(frozenset({card}), events) is False


def test_a_good_grade_finishes_the_card_even_when_it_has_been_shown_once() -> None:
    card = _card_id()
    sitting = _open_sitting(card)
    events = (
        _event(card, sitting.id, Grade.FORGOT),
        _event(card, sitting.id, Grade.GOOD),
    )

    assert sitting.is_finished(frozenset({card}), events) is True


def test_a_card_shown_the_limit_times_is_finished_without_a_good_grade() -> None:
    card = _card_id()
    sitting = _open_sitting(card)
    events = (
        _event(card, sitting.id, Grade.FORGOT),
        _event(card, sitting.id, Grade.HARD),
    )

    assert sitting.is_finished(frozenset({card}), events) is True
    assert sitting.next_card(frozenset({card}), events) is None


def test_discarded_members_do_not_keep_a_sitting_open() -> None:
    present_card = _card_id()
    discarded = _card_id()
    sitting = _open_sitting(present_card, discarded)
    events = (_event(present_card, sitting.id, Grade.GOOD),)

    assert sitting.is_finished(frozenset({present_card}), events) is True


def test_the_same_sitting_and_events_pick_the_same_next_card() -> None:
    first = _card_id()
    second = _card_id()
    sitting = _open_sitting(first, second)
    present = frozenset({first, second})
    events = (_event(first, sitting.id, Grade.FORGOT),)

    first_pick = sitting.next_card(present, events)
    second_pick = sitting.next_card(present, events)

    assert first_pick == second_pick
    assert first_pick in present


def _pinned_sitting(
    sitting_id: str,
    card_ids: tuple[str, ...],
    *,
    showing_limit: int = 2,
) -> Sitting:
    return Sitting(
        id=SittingId(value=UUID(sitting_id)),
        owner_id=_OWNER,
        card_ids=frozenset(CardId(value=UUID(card_id)) for card_id in card_ids),
        opened_at=datetime(2026, 1, 1, tzinfo=UTC),
        showing_limit=ShowingLimit(value=showing_limit),
    )


def _pinned_event(
    card_id: str,
    sitting_id: str,
    reviewed_at: datetime,
    grade: Grade = Grade.FORGOT,
) -> ReviewEvent:
    return ReviewEvent(
        card_id=CardId(value=UUID(card_id)),
        reviewed_at=reviewed_at,
        payload=Graded(grade=grade),
        sitting_id=SittingId(value=UUID(sitting_id)),
    )


def test_the_next_card_is_the_unshown_member_when_one_has_been_shown() -> None:
    sitting_id = "00000000-1111-1111-1111-111111111111"
    shown = "6513270e-269e-0d37-f2a7-4de452e6b438"
    unshown = "d23f0824-128b-2f33-0c5c-7fd0a6a3a450"
    sitting = _pinned_sitting(sitting_id, (shown, unshown))
    present = sitting.card_ids
    events = (_pinned_event(shown, sitting_id, datetime(2026, 1, 1, tzinfo=UTC)),)

    assert sitting.next_card(present, events) == CardId(value=UUID(unshown))


def test_two_sittings_with_the_same_cards_do_not_share_a_draw() -> None:
    card_ids = (
        "6513270e-269e-0d37-f2a7-4de452e6b438",
        "d23f0824-128b-2f33-0c5c-7fd0a6a3a450",
    )
    cards = frozenset(CardId(value=UUID(card_id)) for card_id in card_ids)
    sitting_a = _pinned_sitting("11111111-1111-1111-1111-111111111111", card_ids)
    sitting_b = _pinned_sitting("22222222-2222-2222-2222-222222222222", card_ids)

    pick_a = sitting_a.next_card(cards, ())
    pick_b = sitting_b.next_card(cards, ())

    assert pick_a is not None
    assert pick_b is not None
    assert pick_a != pick_b


def test_event_insertion_order_does_not_change_the_next_card() -> None:
    sitting_id = "5ab7c383-a883-4fdf-ab28-0d827faaea53"
    card_a = "6513270e-269e-0d37-f2a7-4de452e6b438"
    card_b = "d23f0824-128b-2f33-0c5c-7fd0a6a3a450"
    sitting = _pinned_sitting(sitting_id, (card_a, card_b))
    present = sitting.card_ids
    event_a = _pinned_event(card_a, sitting_id, datetime(2026, 1, 2, tzinfo=UTC))
    event_b = _pinned_event(card_b, sitting_id, datetime(2026, 1, 1, tzinfo=UTC))

    pick_b_first = sitting.next_card(present, (event_b, event_a))
    pick_a_first = sitting.next_card(present, (event_a, event_b))

    assert pick_b_first == pick_a_first
    assert pick_b_first == CardId(value=UUID(card_a))


def test_reviews_on_different_cards_change_the_draw_when_counts_tie() -> None:
    sitting_id = "11111111-1111-1111-1111-111111111111"
    card_a = "6513270e-269e-0d37-f2a7-4de452e6b438"
    card_b = "d23f0824-128b-2f33-0c5c-7fd0a6a3a450"
    sitting = _pinned_sitting(sitting_id, (card_a, card_b))
    present = sitting.card_ids
    reviewed_early = datetime(2026, 1, 1, tzinfo=UTC)
    reviewed_late = datetime(2026, 1, 2, tzinfo=UTC)
    card_a_first = (
        _pinned_event(card_a, sitting_id, reviewed_early),
        _pinned_event(card_b, sitting_id, reviewed_late),
    )
    card_b_first = (
        _pinned_event(card_b, sitting_id, reviewed_early),
        _pinned_event(card_a, sitting_id, reviewed_late),
    )

    assert sitting.next_card(present, card_a_first) != sitting.next_card(
        present, card_b_first
    )


def test_a_rejection_finishes_its_card_and_clears_it_from_outstanding() -> None:
    card = _card_id()
    sitting = _open_sitting(card)
    present = frozenset({card})
    events = (_rejection(card, sitting.id),)

    assert sitting.is_finished(present, events) is True
    assert sitting.outstanding(present, events) == frozenset()


def test_a_rejected_card_is_not_drawn_again_while_another_card_remains() -> None:
    rejected = _card_id()
    remaining = _card_id()
    sitting = _open_sitting(rejected, remaining)
    present = frozenset({rejected, remaining})
    events = (_rejection(rejected, sitting.id),)

    assert sitting.is_finished(present, events) is False
    assert sitting.outstanding(present, events) == frozenset({remaining})
    assert sitting.next_card(present, events) == remaining


def test_the_seeded_draw_matches_a_pinned_outcome_for_an_empty_log() -> None:
    sitting_id = "5ab7c383-a883-4fdf-ab28-0d827faaea53"
    card_ids = (
        "6513270e-269e-0d37-f2a7-4de452e6b438",
        "d23f0824-128b-2f33-0c5c-7fd0a6a3a450",
    )
    sitting = _pinned_sitting(sitting_id, card_ids)

    assert sitting.next_card(sitting.card_ids, ()) == CardId(
        value=UUID("6513270e-269e-0d37-f2a7-4de452e6b438")
    )


def _accounted_seed_parts(
    sitting: Sitting, events: tuple[ReviewEvent, ...]
) -> list[tuple[ReviewEvent, str]]:
    accounted: list[tuple[ReviewEvent, str]] = []
    for event in events:
        if event.sitting_id != sitting.id:
            continue
        payload = event.payload
        if isinstance(payload, Graded):
            accounted.append((event, payload.grade))
        elif isinstance(payload, Rejection):
            accounted.append((event, "rejected"))
    return accounted


def _expected_draw_seed(sitting: Sitting, events: tuple[ReviewEvent, ...]) -> int:
    parts = [str(sitting.id.value)]
    ordered = sorted(
        _accounted_seed_parts(sitting, events),
        key=lambda item: (
            item[0].reviewed_at,
            item[0].card_id.value,
            item[1],
            item[0].sitting_id.value,
        ),
    )
    for event, token in ordered:
        parts.extend(
            (
                str(event.card_id.value),
                event.reviewed_at.isoformat(),
                token,
                str(event.sitting_id.value),
            )
        )
    digest = hashlib.sha256("|".join(parts).encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _card_from_seed(pool: frozenset[CardId], seed: int) -> CardId:
    ordered = sorted(pool, key=lambda card_id: card_id.value)
    return ordered[random.Random(seed).randrange(len(ordered))]


def test_draw_seed_includes_event_sitting_id_in_hash_input() -> None:
    sitting_id = "00000000-1111-1111-1111-111111111111"
    card = "6513270e-269e-0d37-f2a7-4de452e6b438"
    sitting = _pinned_sitting(sitting_id, (card,))
    event = _pinned_event(card, sitting_id, datetime(2026, 2, 1, tzinfo=UTC))
    events = (event,)
    present = sitting.card_ids
    expected_seed = _expected_draw_seed(sitting, events)

    assert sitting.next_card(present, events) == _card_from_seed(present, expected_seed)

    parts_without_sitting_id = [
        str(sitting.id.value),
        str(event.card_id.value),
        event.reviewed_at.isoformat(),
        _accounted_seed_parts(sitting, events)[0][1],
        "None",
    ]
    wrong_digest = hashlib.sha256("|".join(parts_without_sitting_id).encode()).digest()
    wrong_seed = int.from_bytes(wrong_digest[:8], "big")
    assert expected_seed != wrong_seed


def test_draw_seed_uses_exactly_eight_digest_bytes_big_endian() -> None:
    sitting_id = "5ab7c383-a883-4fdf-ab28-0d827faaea53"
    card_ids = (
        "6513270e-269e-0d37-f2a7-4de452e6b438",
        "d23f0824-128b-2f33-0c5c-7fd0a6a3a450",
    )
    sitting = _pinned_sitting(sitting_id, card_ids)
    events: tuple[ReviewEvent, ...] = ()
    present = sitting.card_ids

    parts = [str(sitting.id.value)]
    digest = hashlib.sha256("|".join(parts).encode()).digest()
    eight_byte_seed = int.from_bytes(digest[:8], "big")
    nine_byte_seed = int.from_bytes(digest[:9], "big")

    assert _expected_draw_seed(sitting, events) == eight_byte_seed
    assert eight_byte_seed != nine_byte_seed
    assert sitting.next_card(present, events) == _card_from_seed(
        present, eight_byte_seed
    )


def test_a_forgot_grade_and_a_reveal_do_not_finish_a_card_at_the_showing_limit() -> (
    None
):
    card = _card_id()
    sitting = _open_sitting(card)
    present = frozenset({card})
    events = (
        _event(card, sitting.id, Grade.FORGOT),
        _reveal(card, sitting.id),
    )

    assert sitting.is_finished(present, events) is False
    assert sitting.next_card(present, events) == card


def test_two_reveals_do_not_finish_a_card_at_the_showing_limit() -> None:
    card = _card_id()
    sitting = _open_sitting(card)
    present = frozenset({card})
    events = (_reveal(card, sitting.id), _reveal(card, sitting.id))

    assert sitting.is_finished(present, events) is False
    assert sitting.outstanding(present, events) == present
    assert sitting.next_card(present, events) == card


def test_a_reveal_does_not_change_the_next_card_of_an_otherwise_empty_log() -> None:
    sitting_id = "5ab7c383-a883-4fdf-ab28-0d827faaea53"
    card_ids = (
        "6513270e-269e-0d37-f2a7-4de452e6b438",
        "d23f0824-128b-2f33-0c5c-7fd0a6a3a450",
    )
    sitting = _pinned_sitting(sitting_id, card_ids)
    present = sitting.card_ids
    without_reveal = sitting.next_card(present, ())
    revealed = (
        ReviewEvent(
            card_id=CardId(value=UUID(card_ids[0])),
            reviewed_at=datetime(2026, 1, 1, tzinfo=UTC),
            payload=Reveal(),
            sitting_id=SittingId(value=UUID(sitting_id)),
        ),
    )

    assert sitting.next_card(present, revealed) == without_reveal


def test_is_offered_is_false_at_opened_at_plus_resume_horizon() -> None:
    opened_at = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
    horizon = ResumeHorizon(value=timedelta(hours=3))
    sitting = Sitting.open(
        _OWNER,
        frozenset({_card_id()}),
        opened_at,
        ShowingLimit(value=2),
        resume_horizon=horizon,
    )
    boundary = opened_at + horizon.value

    assert sitting.is_offered(boundary - timedelta(microseconds=1)) is True
    assert sitting.is_offered(boundary) is False
