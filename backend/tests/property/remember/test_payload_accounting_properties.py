# pyright: reportUnusedParameter=false
"""Property hunt — remember-flow-source-jump phases 2–3 (payload accounting)."""

from datetime import UTC, datetime, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from domain.remember.due_partition import partition_due
from domain.remember.review_event import ReviewEvent
from domain.remember.review_payload import is_accounting, is_finishing
from domain.remember.sitting import Sitting
from domain.remember.value_objects import (
    CardId,
    Grade,
    Graded,
    Rejection,
    Reveal,
    SchedulerAlgorithm,
    SchedulerStamp,
    ShowingLimit,
    SittingId,
)
from domain.shared.identity.model import UserId

_STAMP = SchedulerStamp(
    algorithm=SchedulerAlgorithm.FSRS,
    parameter_version="payload-hunt",
)
_OWNER = UserId.new()

_GRADES = st.sampled_from(list(Grade))
_PAYLOADS = st.one_of(
    st.builds(Graded, grade=_GRADES),
    st.just(Rejection()),
    st.just(Reveal()),
)


def _card_ids(
    min_size: int = 1, max_size: int = 6
) -> st.SearchStrategy[frozenset[CardId]]:
    return st.lists(
        st.uuids().map(lambda value: CardId(value=value)),
        min_size=min_size,
        max_size=max_size,
        unique_by=lambda card_id: card_id.value,
    ).map(frozenset)


def _sitting(card_ids: frozenset[CardId], limit: int = 2) -> Sitting:
    return Sitting.open(
        _OWNER, card_ids, datetime(2026, 4, 1, tzinfo=UTC), ShowingLimit(value=limit)
    )


def _graded_event(
    card_id: CardId,
    sitting_id: SittingId,
    *,
    grade: Grade = Grade.FORGOT,
    reviewed_at: datetime | None = None,
) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,
        reviewed_at=reviewed_at or datetime(2026, 4, 1, tzinfo=UTC),
        payload=Graded(grade=grade),
        sitting_id=sitting_id,
    )


def _reveal_event(
    card_id: CardId,
    sitting_id: SittingId,
    *,
    reviewed_at: datetime | None = None,
) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,
        reviewed_at=reviewed_at or datetime(2026, 4, 1, tzinfo=UTC),
        payload=Reveal(),
        sitting_id=sitting_id,
    )


@settings(max_examples=100, deadline=30_000)
@given(payload=_PAYLOADS)
def test_is_accounting_matches_graded_rejection_and_not_reveal(
    payload: Graded | Rejection | Reveal,
) -> None:
    expected = isinstance(payload, (Graded, Rejection))
    assert is_accounting(payload) is expected


@settings(max_examples=100, deadline=30_000)
@given(grade=_GRADES)
def test_is_finishing_is_true_for_good_and_easy_grades_only(grade: Grade) -> None:
    assert is_finishing(Graded(grade=grade)) is (grade in (Grade.GOOD, Grade.EASY))


@settings(max_examples=100, deadline=30_000)
@given(card_ids=_card_ids(), reveal_count=st.integers(min_value=0, max_value=12))
def test_only_reveal_events_never_finish_a_single_card_sitting(
    card_ids: frozenset[CardId],
    reveal_count: int,
) -> None:
    sitting = _sitting(card_ids, limit=1)
    present = card_ids
    card = min(card_ids, key=lambda c: c.value)
    events = tuple(
        _reveal_event(
            card,
            sitting.id,
            reviewed_at=datetime(2026, 4, 1, tzinfo=UTC) + timedelta(seconds=index),
        )
        for index in range(reveal_count)
    )

    assert sitting.is_finished(present, events) is False
    assert sitting.outstanding(present, events) == present


@settings(max_examples=100, deadline=30_000)
@given(
    card_ids=_card_ids(min_size=2, max_size=5),
    limit=st.integers(min_value=1, max_value=4),
    extra_reveals=st.lists(
        st.integers(min_value=0, max_value=5), min_size=0, max_size=8
    ),
)
def test_appending_reveal_events_leaves_next_card_unchanged(
    card_ids: frozenset[CardId],
    limit: int,
    extra_reveals: list[int],
) -> None:
    sitting = _sitting(card_ids, limit=limit)
    present = card_ids
    base_events = tuple(
        _graded_event(
            card_id,
            sitting.id,
            grade=Grade.FORGOT,
            reviewed_at=datetime(2026, 4, 1, tzinfo=UTC) + timedelta(hours=index),
        )
        for index, card_id in enumerate(sorted(card_ids, key=lambda c: c.value))
    )
    baseline = sitting.next_card(present, base_events)

    reveal_tail: list[ReviewEvent] = []
    offset = len(base_events)
    for card_index, count in enumerate(extra_reveals):
        target = sorted(card_ids, key=lambda c: c.value)[card_index % len(card_ids)]
        for reveal_index in range(count):
            reveal_tail.append(
                _reveal_event(
                    target,
                    sitting.id,
                    reviewed_at=datetime(2026, 4, 2, tzinfo=UTC)
                    + timedelta(seconds=offset + reveal_index),
                )
            )
        offset += count

    with_reveals = sitting.next_card(present, base_events + tuple(reveal_tail))
    assert with_reveals == baseline


@settings(max_examples=100, deadline=30_000)
@given(
    card_ids=_card_ids(min_size=1, max_size=4),
    grades=st.lists(_GRADES, min_size=0, max_size=6),
    reveal_count=st.integers(min_value=1, max_value=10),
)
def test_reveals_do_not_increment_showing_pressure_toward_finish(
    card_ids: frozenset[CardId],
    grades: list[Grade],
    reveal_count: int,
) -> None:
    sitting = _sitting(card_ids, limit=2)
    present = card_ids
    target = min(card_ids, key=lambda c: c.value)
    graded = tuple(
        _graded_event(
            target,
            sitting.id,
            grade=grade,
            reviewed_at=datetime(2026, 5, 1, tzinfo=UTC) + timedelta(hours=index),
        )
        for index, grade in enumerate(grades)
    )
    finished_without = sitting.is_finished(present, graded)
    reveals = tuple(
        _reveal_event(
            target,
            sitting.id,
            reviewed_at=datetime(2026, 5, 2, tzinfo=UTC) + timedelta(seconds=index),
        )
        for index in range(reveal_count)
    )
    finished_with = sitting.is_finished(present, graded + reveals)
    assert finished_with == finished_without


@settings(max_examples=100, deadline=30_000)
@given(card_ids=_card_ids(min_size=1, max_size=4))
def test_rejection_finishes_a_card_without_a_finishing_grade(
    card_ids: frozenset[CardId],
) -> None:
    sitting = _sitting(card_ids, limit=3)
    present = card_ids
    target = min(card_ids, key=lambda c: c.value)
    events = (
        ReviewEvent(
            card_id=target,
            reviewed_at=datetime(2026, 6, 1, tzinfo=UTC),
            payload=Rejection(),
            sitting_id=sitting.id,
        ),
    )
    assert is_finishing(Rejection()) is True
    assert sitting.is_finished(present, events) is (present == frozenset({target}))


@settings(max_examples=100, deadline=30_000)
@given(
    card_ids=_card_ids(min_size=2, max_size=5),
    reveal_count=st.integers(min_value=1, max_value=8),
)
def test_appending_reveal_events_leaves_outstanding_unchanged(
    card_ids: frozenset[CardId],
    reveal_count: int,
) -> None:
    sitting = _sitting(card_ids, limit=2)
    present = card_ids
    graded = tuple(
        _graded_event(
            card_id,
            sitting.id,
            grade=Grade.HARD,
            reviewed_at=datetime(2026, 6, 2, tzinfo=UTC) + timedelta(hours=index),
        )
        for index, card_id in enumerate(sorted(card_ids, key=lambda c: c.value))
    )
    baseline = sitting.outstanding(present, graded)
    reveals = tuple(
        _reveal_event(
            min(card_ids, key=lambda c: c.value),
            sitting.id,
            reviewed_at=datetime(2026, 6, 3, tzinfo=UTC) + timedelta(seconds=index),
        )
        for index in range(reveal_count)
    )
    assert sitting.outstanding(present, graded + reveals) == baseline


@settings(max_examples=100, deadline=30_000)
@given(
    sitting_cards=_card_ids(min_size=1, max_size=4),
    live=_card_ids(min_size=0, max_size=6),
    reveal_count=st.integers(min_value=1, max_value=6),
)
def test_partition_outstanding_bucket_unchanged_when_only_reveals_are_added(
    sitting_cards: frozenset[CardId],
    live: frozenset[CardId],
    reveal_count: int,
) -> None:
    sitting = _sitting(sitting_cards, limit=2)
    present = sitting.visible(live)
    if not present:
        return
    target = min(present, key=lambda c: c.value)
    baseline = partition_due(
        live, {}, sitting, (), datetime(2026, 6, 1, tzinfo=UTC), _STAMP
    )
    reveals = tuple(
        _reveal_event(
            target,
            sitting.id,
            reviewed_at=datetime(2026, 6, 1, 12, tzinfo=UTC) + timedelta(seconds=index),
        )
        for index in range(reveal_count)
    )
    with_reveals = partition_due(
        live, {}, sitting, reveals, datetime(2026, 6, 1, tzinfo=UTC), _STAMP
    )
    assert with_reveals.total == baseline.total
    assert with_reveals.not_yet_seen + with_reveals.seen_still_owed == (
        baseline.not_yet_seen + baseline.seen_still_owed
    )
