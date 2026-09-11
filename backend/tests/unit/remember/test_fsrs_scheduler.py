import json
import os
import random
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from adapters.out.fsrs.scheduler import FsrsScheduler
from domain.remember.ports import SchedulingReplay
from domain.remember.review_event import ReviewEvent
from domain.remember.scheduling_state import SchedulingState
from domain.remember.value_objects import (
    CardId,
    Grade,
    Graded,
    SchedulerAlgorithm,
    SittingId,
)


def _card_id() -> CardId:
    return CardId(value=uuid4())


def _event(card_id: CardId, *, reviewed_at: datetime, grade: Grade) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,
        reviewed_at=reviewed_at,
        payload=Graded(grade=grade),
        sitting_id=SittingId.new(),
    )


def _growing_log(card_id: CardId, base: datetime) -> tuple[ReviewEvent, ...]:
    """A log whose grades push the interval past the library's fuzz threshold."""
    grades = (Grade.GOOD, Grade.GOOD, Grade.EASY, Grade.EASY, Grade.GOOD, Grade.EASY)
    events: list[ReviewEvent] = []
    reviewed_at = base
    for index, grade in enumerate(grades):
        events.append(_event(card_id, reviewed_at=reviewed_at, grade=grade))
        reviewed_at = reviewed_at + timedelta(days=3 * (index + 1) + 1)
    return tuple(events)


def _review_sequentially(
    scheduler: FsrsScheduler,
    card_id: CardId,
    events: tuple[ReviewEvent, ...],
) -> SchedulingState:
    previous: SchedulingState | None = None
    for event in events:
        payload = event.payload
        assert isinstance(payload, Graded)
        previous = scheduler.review(
            previous,
            card_id,
            payload.grade,
            event.reviewed_at,
        )
    assert previous is not None
    return previous


_SRC = Path(__file__).parents[3] / "src"

_REPLAY_PROBE = """
import json
import sys
from datetime import datetime

from adapters.out.fsrs.scheduler import FsrsScheduler
from domain.remember.ports import SchedulingReplay
from domain.remember.review_event import ReviewEvent
from domain.remember.value_objects import CardId, Grade, Graded, SittingId

log = json.load(sys.stdin)
card_id = CardId(value=log["card_id"])
events = tuple(
    ReviewEvent(
        card_id=card_id,
        reviewed_at=datetime.fromisoformat(event["reviewed_at"]),
        payload=Graded(grade=Grade(event["grade"])),
        sitting_id=SittingId(value=event["sitting_id"]),
    )
    for event in log["events"]
)
state = SchedulingReplay(FsrsScheduler()).replay(card_id, events)
assert state is not None
sys.stdout.write(state.due_at.isoformat())
"""


def _replayed_due_at_in_a_fresh_interpreter(
    card_id: CardId, events: tuple[ReviewEvent, ...], *, hash_seed: str
) -> str:
    """Replay the log in a separate interpreter under a chosen hash salt.

    A seed derived with hash() over str survives only inside one process,
    so this is the only place the difference is observable.
    """
    payload = json.dumps(
        {
            "card_id": str(card_id.value),
            "events": [
                {
                    "reviewed_at": event.reviewed_at.isoformat(),
                    "grade": event.payload.grade.value
                    if isinstance(event.payload, Graded)
                    else event.payload.kind,
                    "sitting_id": str(event.sitting_id.value),
                }
                for event in events
            ],
        }
    )
    completed = subprocess.run(
        [sys.executable, "-c", _REPLAY_PROBE],
        input=payload,
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "PYTHONHASHSEED": hash_seed, "PYTHONPATH": str(_SRC)},
    )
    return completed.stdout


def test_stamp_names_the_fsrs_algorithm_and_the_pinned_parameter_version() -> None:
    stamp = FsrsScheduler().stamp()

    assert stamp.algorithm == SchedulerAlgorithm.FSRS
    assert stamp.parameter_version == "fsrs-6.3.2-defaults"


def test_review_of_a_first_showing_returns_a_state_due_after_the_review_moment() -> (
    None
):
    scheduler = FsrsScheduler()
    card_id = _card_id()
    reviewed_at = datetime(2026, 5, 1, tzinfo=UTC)

    state = scheduler.review(None, card_id, Grade.GOOD, reviewed_at)

    assert state.card_id == card_id
    assert state.stamp == scheduler.stamp()
    assert state.due_at > reviewed_at
    assert state.due_at.tzinfo is not None
    assert state.scheduler_state.payload != {}


def test_review_delays_a_card_further_for_each_better_grade_at_the_same_moment() -> (
    None
):
    scheduler = FsrsScheduler()
    card_id = _card_id()
    reviewed_at = datetime(2026, 5, 1, tzinfo=UTC)

    due_ats = [
        scheduler.review(None, card_id, grade, reviewed_at).due_at
        for grade in (Grade.FORGOT, Grade.HARD, Grade.GOOD, Grade.EASY)
    ]

    assert due_ats == sorted(due_ats)
    assert len(set(due_ats)) == len(due_ats)


def test_review_carrying_a_previous_state_delays_further_than_a_first_showing() -> None:
    scheduler = FsrsScheduler()
    card_id = _card_id()
    first_at = datetime(2026, 5, 1, tzinfo=UTC)
    second_at = first_at + timedelta(days=1)

    first = scheduler.review(None, card_id, Grade.GOOD, first_at)
    second = scheduler.review(first, card_id, Grade.GOOD, second_at)
    fresh = scheduler.review(None, card_id, Grade.GOOD, second_at)

    assert second.due_at - second_at > first.due_at - first_at
    assert second.due_at > fresh.due_at


def test_replay_over_fsrs_reproduces_the_due_at_of_the_sequential_live_path() -> None:
    card_id = _card_id()
    base = datetime(2026, 1, 1, tzinfo=UTC)
    events = _growing_log(card_id, base)

    live = _review_sequentially(FsrsScheduler(), card_id, events)
    replayed = SchedulingReplay(FsrsScheduler()).replay(card_id, events)

    assert replayed is not None
    assert replayed.due_at - events[-1].reviewed_at > timedelta(days=3)
    assert replayed.due_at == live.due_at


def test_review_leaves_the_global_random_generator_state_untouched() -> None:
    scheduler = FsrsScheduler()
    reviewed_at = datetime(2026, 5, 1, tzinfo=UTC)
    random.seed(1234)
    before = random.getstate()

    state = scheduler.review(None, _card_id(), Grade.GOOD, reviewed_at)

    assert state.due_at > reviewed_at
    assert random.getstate() == before


def test_replay_reproduces_the_due_at_in_a_later_process_under_a_different_salt() -> (
    None
):
    card_id = _card_id()
    events = _growing_log(card_id, datetime(2026, 1, 1, tzinfo=UTC))

    live = _review_sequentially(FsrsScheduler(), card_id, events)
    first = _replayed_due_at_in_a_fresh_interpreter(card_id, events, hash_seed="1")
    second = _replayed_due_at_in_a_fresh_interpreter(card_id, events, hash_seed="2")

    assert first == live.due_at.isoformat()
    assert second == first
