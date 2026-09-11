from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from domain.remember.ports import SchedulingReplay
from domain.remember.review_event import ReviewEvent
from domain.remember.scheduling_state import SchedulingState
from domain.remember.value_objects import (
    CardId,
    Grade,
    OpaqueSchedulerState,
    Rejected,
    SchedulerAlgorithm,
    SchedulerStamp,
    SittingId,
)


def _stamp() -> SchedulerStamp:
    return SchedulerStamp(
        algorithm=SchedulerAlgorithm.FSRS,
        parameter_version="test",
    )


def _card_id() -> CardId:
    return CardId(value=uuid4())


def _event(
    card_id: CardId,
    *,
    reviewed_at: datetime,
    grade: Grade,
    sitting_id: SittingId | None = None,
) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,
        reviewed_at=reviewed_at,
        outcome=grade,
        sitting_id=sitting_id or SittingId.new(),
    )


def _rejection(
    card_id: CardId,
    *,
    reviewed_at: datetime,
    sitting_id: SittingId | None = None,
) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,
        reviewed_at=reviewed_at,
        outcome=Rejected.REJECTED,
        sitting_id=sitting_id or SittingId.new(),
    )


class _RecordingScheduler:
    def __init__(self) -> None:
        self.calls: list[tuple[SchedulingState | None, CardId, Grade, datetime]] = []
        self.results: list[SchedulingState] = []
        self._stamp: SchedulerStamp = _stamp()

    def stamp(self) -> SchedulerStamp:
        return self._stamp

    def review(
        self,
        previous: SchedulingState | None,
        card_id: CardId,
        grade: Grade,
        reviewed_at: datetime,
    ) -> SchedulingState:
        self.calls.append((previous, card_id, grade, reviewed_at))
        step = len(self.calls)
        state = SchedulingState(
            card_id=card_id,
            due_at=reviewed_at + timedelta(days=step),
            scheduler_state=OpaqueSchedulerState(payload={"step": step}),
            stamp=self._stamp,
        )
        self.results.append(state)
        return state


def _replay_sequential(
    scheduler: _RecordingScheduler,
    card_id: CardId,
    events: tuple[ReviewEvent, ...],
) -> SchedulingState | None:
    ordered = sorted(events, key=lambda event: event.reviewed_at)
    previous: SchedulingState | None = None
    for event in ordered:
        outcome = event.outcome
        assert isinstance(outcome, Grade)
        previous = scheduler.review(
            previous,
            card_id,
            outcome,
            event.reviewed_at,
        )
    return previous


def test_replay_with_no_events_returns_none() -> None:
    scheduler = _RecordingScheduler()
    replay = SchedulingReplay(scheduler)

    assert replay.replay(_card_id(), ()) is None
    assert scheduler.calls == []


def test_replay_processes_events_in_reviewed_at_order_not_input_order() -> None:
    card_id = _card_id()
    earlier = datetime(2026, 1, 1, tzinfo=UTC)
    later = datetime(2026, 1, 2, tzinfo=UTC)
    events = (
        _event(card_id, reviewed_at=later, grade=Grade.HARD),
        _event(card_id, reviewed_at=earlier, grade=Grade.FORGOT),
    )
    scheduler = _RecordingScheduler()
    replay = SchedulingReplay(scheduler)

    _ = replay.replay(card_id, events)

    assert [call[3] for call in scheduler.calls] == [earlier, later]
    assert [call[2] for call in scheduler.calls] == [Grade.FORGOT, Grade.HARD]


def test_replay_threads_each_scheduler_result_as_the_next_previous_state() -> None:
    card_id = _card_id()
    base = datetime(2026, 1, 1, tzinfo=UTC)
    events = (
        _event(card_id, reviewed_at=base, grade=Grade.FORGOT),
        _event(card_id, reviewed_at=base + timedelta(hours=1), grade=Grade.GOOD),
    )
    scheduler = _RecordingScheduler()
    replay = SchedulingReplay(scheduler)

    _ = replay.replay(card_id, events)

    assert scheduler.calls[0][0] is None
    assert scheduler.calls[1][0] == scheduler.results[0]


def test_replay_of_n_events_matches_n_sequential_live_reviews() -> None:
    card_id = _card_id()
    base = datetime(2026, 3, 1, tzinfo=UTC)
    events = (
        _event(card_id, reviewed_at=base, grade=Grade.FORGOT),
        _event(card_id, reviewed_at=base + timedelta(days=1), grade=Grade.HARD),
        _event(card_id, reviewed_at=base + timedelta(days=2), grade=Grade.GOOD),
    )
    live_scheduler = _RecordingScheduler()
    replay_scheduler = _RecordingScheduler()
    replay = SchedulingReplay(replay_scheduler)

    expected = _replay_sequential(live_scheduler, card_id, events)
    actual = replay.replay(card_id, events)

    assert actual == expected
    assert actual is not None
    assert actual.due_at == base + timedelta(days=5)


def test_a_rejection_only_log_replays_to_none_without_scheduling() -> None:
    card_id = _card_id()
    events = (
        _rejection(card_id, reviewed_at=datetime(2026, 5, 1, tzinfo=UTC)),
        _rejection(card_id, reviewed_at=datetime(2026, 5, 2, tzinfo=UTC)),
    )
    scheduler = _RecordingScheduler()
    replay = SchedulingReplay(scheduler)

    assert replay.replay(card_id, events) is None
    assert scheduler.calls == []


def test_replay_of_a_mixed_log_matches_replaying_the_grades_alone() -> None:
    card_id = _card_id()
    first_grade_at = datetime(2026, 6, 1, tzinfo=UTC)
    rejected_at = datetime(2026, 6, 2, tzinfo=UTC)
    second_grade_at = datetime(2026, 6, 3, tzinfo=UTC)
    mixed = (
        _event(card_id, reviewed_at=first_grade_at, grade=Grade.FORGOT),
        _rejection(card_id, reviewed_at=rejected_at),
        _event(card_id, reviewed_at=second_grade_at, grade=Grade.GOOD),
    )
    grades_only = (
        _event(card_id, reviewed_at=first_grade_at, grade=Grade.FORGOT),
        _event(card_id, reviewed_at=second_grade_at, grade=Grade.GOOD),
    )
    mixed_scheduler = _RecordingScheduler()
    grades_scheduler = _RecordingScheduler()

    mixed_result = SchedulingReplay(mixed_scheduler).replay(card_id, mixed)
    grades_result = SchedulingReplay(grades_scheduler).replay(card_id, grades_only)

    assert mixed_result == grades_result
    assert mixed_result is not None
    assert [call[2] for call in mixed_scheduler.calls] == [Grade.FORGOT, Grade.GOOD]
    assert Rejected.REJECTED not in [call[2] for call in mixed_scheduler.calls]


def test_replay_skips_foreign_cards_without_stopping_on_later_target_grades() -> None:
    """Foreign card_id must continue the loop, not break it."""
    card_a = CardId(value=UUID("a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1"))
    card_b = CardId(value=UUID("b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2"))
    base = datetime(2026, 9, 1, tzinfo=UTC)
    events = (
        _event(card_a, reviewed_at=base, grade=Grade.FORGOT),
        _event(card_b, reviewed_at=base + timedelta(hours=1), grade=Grade.FORGOT),
        _event(card_a, reviewed_at=base + timedelta(hours=2), grade=Grade.GOOD),
    )
    scheduler = _RecordingScheduler()
    replay = SchedulingReplay(scheduler)

    result = replay.replay(card_a, events)

    assert result is not None
    assert len(scheduler.calls) == 2
    assert [call[2] for call in scheduler.calls] == [Grade.FORGOT, Grade.GOOD]


def test_replay_for_one_card_ignores_another_cards_grades_in_the_sequence() -> None:
    card_a = CardId(value=UUID("e3e70682-c209-4cac-629f-6fbed82c07cd"))
    card_b = CardId(value=UUID("f728b4fa-4248-5e3a-0a5d-2f346baa9455"))
    base = datetime(2026, 8, 1, tzinfo=UTC)
    mixed = (
        _event(card_a, reviewed_at=base, grade=Grade.FORGOT),
        _event(card_b, reviewed_at=base + timedelta(hours=1), grade=Grade.FORGOT),
    )
    card_a_only = (mixed[0],)
    mixed_scheduler = _RecordingScheduler()
    scoped_scheduler = _RecordingScheduler()

    mixed_result = SchedulingReplay(mixed_scheduler).replay(card_a, mixed)
    scoped_result = SchedulingReplay(scoped_scheduler).replay(card_a, card_a_only)

    assert mixed_result == scoped_result
    assert len(mixed_scheduler.calls) == 1
    assert mixed_scheduler.calls[0][1:] == (card_a, Grade.FORGOT, base)


def test_replay_ignores_each_event_sitting_id_when_calling_the_scheduler() -> None:
    card_id = _card_id()
    reviewed_at = datetime(2026, 4, 1, tzinfo=UTC)
    events = (
        _event(
            card_id,
            reviewed_at=reviewed_at,
            grade=Grade.EASY,
            sitting_id=SittingId.new(),
        ),
    )
    scheduler = _RecordingScheduler()
    replay = SchedulingReplay(scheduler)

    result = replay.replay(card_id, events)

    assert result is not None
    assert len(scheduler.calls) == 1
    assert scheduler.calls[0][1:] == (card_id, Grade.EASY, reviewed_at)
