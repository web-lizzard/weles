# pyright: reportUnusedParameter=false
"""Property hunt over partition_due (remember-flow-due-count phase 2)."""

from datetime import UTC, datetime, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from domain.remember.due_partition import partition_due
from domain.remember.review_event import ReviewEvent
from domain.remember.scheduling_state import SchedulingState, due_card_ids
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

_STAMP = SchedulerStamp(
    algorithm=SchedulerAlgorithm.FSRS,
    parameter_version="due-partition-hunt",
)
_AS_OF = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

_GRADES = st.sampled_from(list(Grade))


def _card_ids(
    min_size: int = 1, max_size: int = 6
) -> st.SearchStrategy[frozenset[CardId]]:
    return st.lists(
        st.uuids().map(lambda value: CardId(value=value)),
        min_size=min_size,
        max_size=max_size,
        unique_by=lambda card_id: card_id.value,
    ).map(frozenset)


@st.composite
def _live_and_states(
    draw: st.DrawFn,
) -> tuple[frozenset[CardId], dict[CardId, SchedulingState]]:
    live = draw(_card_ids(min_size=0, max_size=8))
    states: dict[CardId, SchedulingState] = {}
    for card_id in live:
        due = draw(st.booleans())
        due_at = (
            _AS_OF - timedelta(hours=1)
            if due
            else _AS_OF + timedelta(days=draw(st.integers(min_value=1, max_value=30)))
        )
        states[card_id] = SchedulingState(
            card_id=card_id,
            due_at=due_at,
            scheduler_state=OpaqueSchedulerState(payload={}),
            stamp=_STAMP,
        )
    return live, states


def _event(
    card_id: CardId,
    sitting_id: SittingId,
    *,
    grade: Grade = Grade.FORGOT,
) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,
        reviewed_at=_AS_OF,
        payload=Graded(grade=grade),
        sitting_id=sitting_id,
    )


def _sitting(card_ids: frozenset[CardId], *, limit: int = 2) -> Sitting:
    return Sitting.open(
        card_ids,
        datetime(2026, 5, 1, tzinfo=UTC),
        ShowingLimit(value=limit),
    )


@settings(max_examples=100, deadline=30_000)
@given(drawn=_live_and_states())
def test_without_a_sitting_total_matches_due_card_ids_and_sits_in_not_yet_seen(
    drawn: tuple[frozenset[CardId], dict[CardId, SchedulingState]],
) -> None:
    live, states = drawn
    partition = partition_due(live, states, None, (), _AS_OF, _STAMP)
    expected_total = len(due_card_ids(live, states, _AS_OF, _STAMP))

    assert partition.total == expected_total
    assert partition.not_yet_seen == expected_total
    assert partition.seen_still_owed == 0
    assert partition.ripe_outside_sitting == 0


@settings(max_examples=100, deadline=30_000)
@given(
    sitting_cards=_card_ids(min_size=1, max_size=5),
    live=_card_ids(min_size=0, max_size=8),
    limit=st.integers(min_value=1, max_value=4),
)
def test_with_a_sitting_total_equals_the_due_union_outstanding_cardinality(
    sitting_cards: frozenset[CardId],
    live: frozenset[CardId],
    limit: int,
) -> None:
    sitting = _sitting(sitting_cards, limit=limit)
    present = sitting.visible(live)
    outstanding = sitting.outstanding(present, ())
    due = due_card_ids(live, {}, _AS_OF, _STAMP)
    expected_total = len(due | outstanding)

    partition = partition_due(live, {}, sitting, (), _AS_OF, _STAMP)

    assert partition.total == expected_total
    assert (
        partition.not_yet_seen
        + partition.seen_still_owed
        + partition.ripe_outside_sitting
        == partition.total
    )


@settings(max_examples=100, deadline=30_000)
@given(
    sitting_cards=_card_ids(min_size=2, max_size=5),
    live=_card_ids(min_size=2, max_size=6),
    grades=st.lists(_GRADES, min_size=1, max_size=6),
)
def test_foreign_sitting_review_events_do_not_change_the_partition(
    sitting_cards: frozenset[CardId],
    live: frozenset[CardId],
    grades: list[Grade],
) -> None:
    sitting = _sitting(sitting_cards)
    present = sitting.visible(live)
    if not present:
        return
    own_events = tuple(
        _event(card_id, sitting.id, grade=grade)
        for card_id, grade in zip(
            sorted(present, key=lambda c: c.value), grades, strict=False
        )
    )
    foreign = SittingId.new()
    foreign_events = tuple(
        _event(card_id, foreign, grade=Grade.GOOD) for card_id in present
    )

    baseline = partition_due(live, {}, sitting, own_events, _AS_OF, _STAMP)
    with_foreign = partition_due(
        live, {}, sitting, own_events + foreign_events, _AS_OF, _STAMP
    )

    assert baseline == with_foreign


@settings(max_examples=100, deadline=30_000)
@given(
    sitting_cards=_card_ids(min_size=1, max_size=4),
    live=_card_ids(min_size=1, max_size=6),
    extra_events=st.lists(_GRADES, min_size=0, max_size=8),
)
def test_seen_still_owed_counts_at_most_one_per_outstanding_card(
    sitting_cards: frozenset[CardId],
    live: frozenset[CardId],
    extra_events: list[Grade],
) -> None:
    sitting = _sitting(sitting_cards)
    present = sitting.visible(live)
    outstanding = sitting.outstanding(present, ())
    if not outstanding:
        return

    target = min(outstanding, key=lambda card_id: card_id.value)
    events = tuple(_event(target, sitting.id, grade=grade) for grade in extra_events)
    partition = partition_due(live, {}, sitting, events, _AS_OF, _STAMP)

    assert partition.seen_still_owed <= len(outstanding)
    assert partition.not_yet_seen <= len(outstanding)


@st.composite
def _sitting_scenario(
    draw: st.DrawFn,
) -> tuple[
    frozenset[CardId],
    dict[CardId, SchedulingState],
    Sitting,
    tuple[ReviewEvent, ...],
]:
    live, states = draw(_live_and_states())
    sitting_cards = draw(
        st.sets(
            st.sampled_from(sorted(live, key=lambda c: c.value) if live else []),
            min_size=1,
            max_size=min(5, len(live) or 1),
        ).map(frozenset)
        if live
        else _card_ids(min_size=1, max_size=3)
    )
    if not live:
        live = sitting_cards
        for card_id in sitting_cards:
            states[card_id] = SchedulingState(
                card_id=card_id,
                due_at=_AS_OF + timedelta(days=1),
                scheduler_state=OpaqueSchedulerState(payload={}),
                stamp=_STAMP,
            )
    limit = draw(st.integers(min_value=1, max_value=4))
    sitting = _sitting(sitting_cards, limit=limit)
    present = sitting.visible(live)
    if not present:
        return live, states, sitting, ()
    graded = draw(
        st.lists(
            st.tuples(
                st.sampled_from(sorted(present, key=lambda c: c.value)),
                _GRADES,
            ),
            min_size=0,
            max_size=8,
        )
    )
    events = tuple(
        _event(card_id, sitting.id, grade=grade) for card_id, grade in graded
    )
    return live, states, sitting, events


@settings(max_examples=100, deadline=30_000)
@given(scenario=_sitting_scenario())
def test_with_scheduler_states_total_matches_due_union_outstanding_cardinality(
    scenario: tuple[
        frozenset[CardId],
        dict[CardId, SchedulingState],
        Sitting,
        tuple[ReviewEvent, ...],
    ],
) -> None:
    live, states, sitting, events = scenario
    present = sitting.visible(live)
    outstanding = sitting.outstanding(present, events)
    due = due_card_ids(live, states, _AS_OF, _STAMP)
    expected_total = len(due | outstanding)

    partition = partition_due(live, states, sitting, events, _AS_OF, _STAMP)

    assert partition.total == expected_total
    assert (
        partition.not_yet_seen
        + partition.seen_still_owed
        + partition.ripe_outside_sitting
        == partition.total
    )


@settings(max_examples=100, deadline=30_000)
@given(scenario=_sitting_scenario())
def test_outstanding_members_split_exactly_between_not_yet_seen_and_seen_still_owed(
    scenario: tuple[
        frozenset[CardId],
        dict[CardId, SchedulingState],
        Sitting,
        tuple[ReviewEvent, ...],
    ],
) -> None:
    live, states, sitting, events = scenario
    present = sitting.visible(live)
    outstanding = sitting.outstanding(present, events)
    due = due_card_ids(live, states, _AS_OF, _STAMP)
    total_set = due | outstanding

    partition = partition_due(live, states, sitting, events, _AS_OF, _STAMP)

    shown_in_sitting = frozenset(
        card_id
        for card_id in outstanding
        if any(
            event.card_id == card_id and event.sitting_id == sitting.id
            for event in events
        )
    )
    unshown_outstanding = outstanding - shown_in_sitting
    ripe = total_set - outstanding

    assert partition.seen_still_owed == len(shown_in_sitting)
    assert partition.not_yet_seen == len(unshown_outstanding)
    assert partition.ripe_outside_sitting == len(ripe)


@st.composite
def _sitting_scenario_with_noise(
    draw: st.DrawFn,
) -> tuple[
    frozenset[CardId],
    dict[CardId, SchedulingState],
    Sitting,
    tuple[ReviewEvent, ...],
    tuple[ReviewEvent, ...],
]:
    live, states, sitting, events = draw(_sitting_scenario())
    noise_cards = draw(
        st.lists(
            st.uuids().map(lambda value: CardId(value=value)),
            min_size=0,
            max_size=4,
            unique=True,
        )
    )
    noise = tuple(
        _event(card_id, sitting.id, grade=Grade.GOOD) for card_id in noise_cards
    )
    return live, states, sitting, events, noise


@settings(max_examples=100, deadline=30_000)
@given(scenario=_sitting_scenario_with_noise())
def test_partition_is_unchanged_when_events_for_cards_not_in_the_sitting_are_appended(
    scenario: tuple[
        frozenset[CardId],
        dict[CardId, SchedulingState],
        Sitting,
        tuple[ReviewEvent, ...],
        tuple[ReviewEvent, ...],
    ],
) -> None:
    live, states, sitting, events, noise = scenario
    baseline = partition_due(live, states, sitting, events, _AS_OF, _STAMP)
    with_noise = partition_due(live, states, sitting, events + noise, _AS_OF, _STAMP)
    assert baseline == with_noise
