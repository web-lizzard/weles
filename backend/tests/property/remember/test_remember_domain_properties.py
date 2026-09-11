# pyright: reportUnusedParameter=false
"""Property tests over remember domain phases 2–4 (membership, ordering, replay)."""

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from hypothesis import example, given, settings
from hypothesis import strategies as st

from domain.remember.ports import SchedulingReplay
from domain.remember.review_event import ReviewEvent
from domain.remember.scheduling_state import SchedulingState, card_is_due
from domain.remember.sitting import Sitting
from domain.remember.value_objects import (
    CardId,
    Grade,
    Graded,
    OpaqueSchedulerState,
    SchedulerAlgorithm,
    SchedulerStamp,
    ShowingLimit,
    SittingId,
)

_GRADES = st.sampled_from(list(Grade))
_STAMP = SchedulerStamp(
    algorithm=SchedulerAlgorithm.FSRS,
    parameter_version="property-hunt",
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
        card_ids, datetime(2026, 1, 1, tzinfo=UTC), ShowingLimit(value=limit)
    )


def _event(
    card_id: CardId,
    sitting_id: SittingId,
    *,
    reviewed_at: datetime | None = None,
    grade: Grade = Grade.FORGOT,
) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,
        reviewed_at=reviewed_at or datetime(2026, 1, 1, tzinfo=UTC),
        payload=Graded(grade=grade),
        sitting_id=sitting_id,
    )


class _LinearScheduler:
    def stamp(self) -> SchedulerStamp:
        return _STAMP

    def review(
        self,
        previous: SchedulingState | None,
        card_id: CardId,
        grade: Grade,
        reviewed_at: datetime,
    ) -> SchedulingState:
        step = (
            1
            if previous is None
            else cast(int, previous.scheduler_state.payload["step"]) + 1
        )
        return SchedulingState(
            card_id=card_id,
            due_at=reviewed_at + timedelta(days=step),
            scheduler_state=OpaqueSchedulerState(
                payload={"step": step, "grade": grade.value}
            ),
            stamp=_STAMP,
        )


def _sequential_replay(
    scheduler: _LinearScheduler,
    card_id: CardId,
    events: tuple[ReviewEvent, ...],
) -> SchedulingState | None:
    ordered = sorted(events, key=lambda event: event.reviewed_at)
    previous: SchedulingState | None = None
    for event in ordered:
        payload = event.payload
        assert isinstance(payload, Graded)
        previous = scheduler.review(previous, card_id, payload.grade, event.reviewed_at)
    return previous


@settings(max_examples=100, deadline=None)
@given(card_ids=_card_ids(), live=_card_ids(min_size=0, max_size=8))
def test_visible_is_exactly_the_intersection_and_never_mutates_membership(
    card_ids: frozenset[CardId],
    live: frozenset[CardId],
) -> None:
    sitting = _sitting(card_ids)
    stored = sitting.card_ids

    visible = sitting.visible(live)

    assert visible == card_ids & live
    assert visible <= card_ids
    assert visible <= live
    assert sitting.card_ids == stored


@settings(max_examples=100, deadline=None)
@given(
    due_at=st.datetimes(timezones=st.just(UTC)),
    as_of=st.datetimes(timezones=st.just(UTC)),
)
def test_card_is_due_is_monotonic_in_as_of_when_stamp_matches(
    due_at: datetime,
    as_of: datetime,
) -> None:
    state = SchedulingState(
        card_id=CardId(value=uuid4()),
        due_at=due_at,
        scheduler_state=OpaqueSchedulerState(payload={}),
        stamp=_STAMP,
    )
    if card_is_due(state, as_of, _STAMP):
        later = as_of + timedelta(seconds=1)
        assert card_is_due(state, later, _STAMP)


@settings(max_examples=100, deadline=None)
@given(card_ids=_card_ids(), present=_card_ids(min_size=0, max_size=6))
def test_next_card_is_deterministic_and_lies_in_present_when_returned(
    card_ids: frozenset[CardId],
    present: frozenset[CardId],
) -> None:
    sitting = _sitting(card_ids)
    present_in_sitting = present & card_ids
    events: tuple[ReviewEvent, ...] = ()

    first = sitting.next_card(present_in_sitting, events)
    second = sitting.next_card(present_in_sitting, events)

    assert first == second
    if first is not None:
        assert first in present_in_sitting


@settings(max_examples=100, deadline=None)
@given(card_ids=_card_ids(min_size=2, max_size=5))
def test_foreign_sitting_events_do_not_change_next_card_or_finish_state(
    card_ids: frozenset[CardId],
) -> None:
    sitting = _sitting(card_ids)
    present = card_ids
    own_events = tuple(
        _event(card_id, sitting.id, grade=Grade.FORGOT) for card_id in card_ids
    )
    foreign_events = tuple(
        _event(card_id, SittingId.new(), grade=Grade.GOOD) for card_id in card_ids
    )

    without_foreign = sitting.next_card(present, own_events)
    with_foreign = sitting.next_card(present, own_events + foreign_events)
    assert without_foreign == with_foreign

    finished_without = sitting.is_finished(present, own_events)
    finished_with = sitting.is_finished(present, own_events + foreign_events)
    assert finished_without == finished_with


def test_foreign_sitting_events_must_not_change_the_drawn_next_card() -> None:
    card_ids = frozenset(
        {
            CardId(value=UUID("6513270e-269e-0d37-f2a7-4de452e6b438")),
            CardId(value=UUID("d23f0824-128b-2f33-0c5c-7fd0a6a3a450")),
        }
    )
    sitting = Sitting(
        id=SittingId(value=UUID("5ab7c383-a883-4fdf-ab28-0d827faaea53")),
        card_ids=card_ids,
        opened_at=datetime(2026, 1, 1, tzinfo=UTC),
        showing_limit=ShowingLimit(value=2),
    )
    present = card_ids
    own_events = tuple(
        _event(card_id, sitting.id, grade=Grade.FORGOT) for card_id in card_ids
    )
    foreign_sitting = SittingId(value=UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"))
    foreign_events = tuple(
        _event(card_id, foreign_sitting, grade=Grade.GOOD) for card_id in card_ids
    )

    without_foreign = sitting.next_card(present, own_events)
    with_foreign = sitting.next_card(present, own_events + foreign_events)

    assert without_foreign == with_foreign


@settings(max_examples=100, deadline=None)
@given(
    card_id=st.uuids().map(lambda value: CardId(value=value)),
    grades=st.lists(_GRADES, min_size=1, max_size=8),
)
def test_replay_matches_sequential_live_review(
    card_id: CardId, grades: list[Grade]
) -> None:
    base = datetime(2026, 2, 1, tzinfo=UTC)
    events = tuple(
        ReviewEvent(
            card_id=card_id,
            reviewed_at=base + timedelta(hours=index),
            payload=Graded(grade=grade),
            sitting_id=SittingId.new(),
        )
        for index, grade in enumerate(grades)
    )
    scheduler = _LinearScheduler()
    replay = SchedulingReplay(scheduler)

    assert replay.replay(card_id, events) == _sequential_replay(
        scheduler, card_id, events
    )


@settings(max_examples=100, deadline=None)
@given(
    card_id=st.uuids().map(lambda value: CardId(value=value)),
    grades=st.lists(_GRADES, min_size=1, max_size=6),
)
def test_replay_is_invariant_under_event_order_permutation(
    card_id: CardId,
    grades: list[Grade],
) -> None:
    base = datetime(2026, 3, 1, tzinfo=UTC)
    events = [
        ReviewEvent(
            card_id=card_id,
            reviewed_at=base + timedelta(hours=index),
            payload=Graded(grade=grade),
            sitting_id=SittingId.new(),
        )
        for index, grade in enumerate(grades)
    ]
    replay = SchedulingReplay(_LinearScheduler())

    canonical = replay.replay(card_id, tuple(events))
    reversed_input = replay.replay(card_id, tuple(reversed(events)))

    assert canonical == reversed_input


@settings(max_examples=100, deadline=None)
@given(
    card_ids=_card_ids(min_size=1, max_size=4),
    limit=st.integers(min_value=1, max_value=5),
)
def test_next_card_never_returns_a_finished_card(
    card_ids: frozenset[CardId],
    limit: int,
) -> None:
    sitting = Sitting.open(
        card_ids,
        datetime(2026, 5, 1, tzinfo=UTC),
        ShowingLimit(value=limit),
    )
    present = card_ids
    events = tuple(
        _event(card_id, sitting.id, grade=Grade.GOOD) for card_id in card_ids
    )

    if sitting.is_finished(present, events):
        assert sitting.next_card(present, events) is None
    else:
        pick = sitting.next_card(present, events)
        if pick is not None:
            sitting_events = tuple(
                event for event in events if event.sitting_id == sitting.id
            )
            finished = (
                any(
                    event.card_id == pick
                    and isinstance(event.payload, Graded)
                    and event.payload.grade in {Grade.GOOD, Grade.EASY}
                    for event in sitting_events
                )
                or sum(1 for event in sitting_events if event.card_id == pick) >= limit
            )
            assert not finished


@settings(max_examples=100, deadline=None)
@given(
    card_a=st.uuids().map(lambda value: CardId(value=value)),
    card_b=st.uuids().map(lambda value: CardId(value=value)),
    grade_a=_GRADES,
    grade_b=_GRADES,
)
@example(
    card_a=CardId(value=UUID("e3e70682-c209-4cac-629f-6fbed82c07cd")),
    card_b=CardId(value=UUID("f728b4fa-4248-5e3a-0a5d-2f346baa9455")),
    grade_a=Grade.FORGOT,
    grade_b=Grade.FORGOT,
)
def test_replay_ignores_grades_belonging_to_other_cards(
    card_a: CardId,
    card_b: CardId,
    grade_a: Grade,
    grade_b: Grade,
) -> None:
    if card_a.value == card_b.value:
        return
    base = datetime(2026, 8, 1, tzinfo=UTC)
    events = (
        ReviewEvent(
            card_id=card_a,
            reviewed_at=base,
            payload=Graded(grade=grade_a),
            sitting_id=SittingId.new(),
        ),
        ReviewEvent(
            card_id=card_b,
            reviewed_at=base + timedelta(hours=1),
            payload=Graded(grade=grade_b),
            sitting_id=SittingId.new(),
        ),
    )
    replay = SchedulingReplay(_LinearScheduler())
    scoped = tuple(event for event in events if event.card_id == card_a)
    assert replay.replay(card_a, events) == replay.replay(card_a, scoped)
