from datetime import UTC, datetime, timedelta
from uuid import uuid4

from domain.remember.ports import SchedulingReplay
from domain.remember.review_event import ReviewEvent
from domain.remember.scheduling_state import SchedulingState
from domain.remember.value_objects import (
    CardId,
    Grade,
    OpaqueSchedulerState,
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
        grade=grade,
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
        previous = scheduler.review(
            previous,
            card_id,
            event.grade,
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
