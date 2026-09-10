from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from application.remember.commands.grade_card import GradeCardCommand
from application.remember.dto import GradeAppliedDTO
from domain.remember.exceptions import (
    CardNotInSittingError,
    CardNotPresentableError,
    SittingAlreadyCompleteError,
    SittingNotFoundError,
)
from domain.remember.ports import ReviewableCard, SchedulingReplay
from domain.remember.review_event import ReviewEvent
from domain.remember.scheduling_state import SchedulingState
from domain.remember.sitting import Sitting
from domain.remember.value_objects import (
    CardId,
    Grade,
    OpaqueSchedulerState,
    SchedulerAlgorithm,
    SchedulerStamp,
    ShowingLimit,
    SittingId,
)


def _card_id() -> CardId:
    return CardId(value=uuid4())


def _reviewable(
    card_id: CardId | None = None,
    *,
    front: str = "What is ARP?",
    back: str = "MAC from IP.",
) -> ReviewableCard:
    return ReviewableCard(id=card_id or _card_id(), front=front, back=back)


def _open_sitting(*cards: ReviewableCard) -> Sitting:
    return Sitting.open(
        frozenset(card.id for card in cards),
        datetime.now(UTC),
        ShowingLimit(value=2),
    )


def _stamp(parameter_version: str = "fsrs-6.3.2-defaults") -> SchedulerStamp:
    return SchedulerStamp(
        algorithm=SchedulerAlgorithm.FSRS,
        parameter_version=parameter_version,
    )


def _state(
    card_id: CardId,
    *,
    due_at: datetime,
    stamp: SchedulerStamp,
    payload: dict[str, object] | None = None,
) -> SchedulingState:
    return SchedulingState(
        card_id=card_id,
        due_at=due_at,
        scheduler_state=OpaqueSchedulerState(payload=payload or {"memo": True}),
        stamp=stamp,
    )


def _event(
    card_id: CardId,
    sitting_id: SittingId,
    grade: Grade,
    *,
    reviewed_at: datetime | None = None,
) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,
        reviewed_at=reviewed_at or datetime.now(UTC),
        grade=grade,
        sitting_id=sitting_id,
    )


class _Clock:
    def __init__(self, instant: datetime) -> None:
        self._instant: datetime = instant

    def now(self) -> datetime:
        return self._instant


class _RecordingScheduler:
    def __init__(self, stamp: SchedulerStamp) -> None:
        self._stamp: SchedulerStamp = stamp
        self.calls: list[tuple[SchedulingState | None, CardId, Grade, datetime]] = []
        self.results: list[SchedulingState] = []

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


class _Catalog:
    def __init__(self, cards: Sequence[ReviewableCard]) -> None:
        self._cards: dict[CardId, ReviewableCard] = {card.id: card for card in cards}

    async def list_reviewable(self) -> Sequence[ReviewableCard]:
        return list(self._cards.values())

    async def get_reviewable(self, card_id: CardId) -> ReviewableCard | None:
        return self._cards.get(card_id)


class _SittingRepository:
    def __init__(self) -> None:
        self._sittings: dict[SittingId, Sitting] = {}

    async def save(self, sitting: Sitting) -> None:
        self._sittings[sitting.id] = sitting

    async def get(self, sitting_id: SittingId) -> Sitting | None:
        return self._sittings.get(sitting_id)


class _ReviewEventStore:
    def __init__(self, events: Sequence[ReviewEvent] = ()) -> None:
        self._events: list[ReviewEvent] = list(events)
        self.saved: list[ReviewEvent] = []

    async def save(self, event: ReviewEvent) -> None:
        self.saved.append(event)
        self._events.append(event)

    async def list_by_card(self, card_id: CardId) -> Sequence[ReviewEvent]:
        return tuple(
            sorted(
                (event for event in self._events if event.card_id == card_id),
                key=lambda event: event.reviewed_at,
            )
        )

    async def list_by_sitting(self, sitting_id: SittingId) -> Sequence[ReviewEvent]:
        return tuple(
            sorted(
                (event for event in self._events if event.sitting_id == sitting_id),
                key=lambda event: event.reviewed_at,
            )
        )


class _SchedulingStateRepository:
    def __init__(self, states: dict[CardId, SchedulingState] | None = None) -> None:
        self._states: dict[CardId, SchedulingState] = dict(states or {})
        self.saved: list[SchedulingState] = []

    async def save(self, state: SchedulingState) -> None:
        self.saved.append(state)
        self._states[state.card_id] = state

    async def get(self, card_id: CardId) -> SchedulingState | None:
        return self._states.get(card_id)

    async def get_many(
        self, card_ids: Sequence[CardId]
    ) -> dict[CardId, SchedulingState]:
        return {
            card_id: self._states[card_id]
            for card_id in card_ids
            if card_id in self._states
        }


class _UnitOfWork:
    def __init__(
        self,
        sittings: _SittingRepository,
        scheduling_states: _SchedulingStateRepository,
        review_events: _ReviewEventStore,
    ) -> None:
        self.sittings: _SittingRepository = sittings
        self.scheduling_states: _SchedulingStateRepository = scheduling_states
        self.review_events: _ReviewEventStore = review_events
        self.committed: bool = False

    async def __aenter__(self) -> "_UnitOfWork":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True


def _command(
    *,
    catalog: _Catalog,
    events: Sequence[ReviewEvent] = (),
    states: dict[CardId, SchedulingState] | None = None,
    as_of: datetime | None = None,
    stamp: SchedulerStamp | None = None,
) -> tuple[
    GradeCardCommand,
    _ReviewEventStore,
    _SchedulingStateRepository,
    _RecordingScheduler,
    datetime,
    _UnitOfWork,
]:
    instant = as_of or datetime.now(UTC)
    sittings = _SittingRepository()
    review_events = _ReviewEventStore(events)
    scheduling_states = _SchedulingStateRepository(states)
    scheduler = _RecordingScheduler(stamp or _stamp())
    uow = _UnitOfWork(sittings, scheduling_states, review_events)

    def uow_factory() -> _UnitOfWork:
        return uow

    command = GradeCardCommand(
        uow_factory,  # pyright: ignore[reportArgumentType]
        catalog,
        scheduler,
        _Clock(instant),
    )
    return command, review_events, scheduling_states, scheduler, instant, uow


async def _saved_command(
    *,
    sitting: Sitting,
    catalog: _Catalog,
    events: Sequence[ReviewEvent] = (),
    states: dict[CardId, SchedulingState] | None = None,
    as_of: datetime | None = None,
    stamp: SchedulerStamp | None = None,
) -> tuple[
    GradeCardCommand,
    _ReviewEventStore,
    _SchedulingStateRepository,
    _RecordingScheduler,
    datetime,
    _UnitOfWork,
]:
    command, events_store, states_repo, scheduler, instant, uow = _command(
        catalog=catalog,
        events=events,
        states=states,
        as_of=as_of,
        stamp=stamp,
    )
    await uow.sittings.save(sitting)
    return command, events_store, states_repo, scheduler, instant, uow


async def test_an_unknown_sitting_raises_sitting_not_found() -> None:
    card = _reviewable()
    sitting = _open_sitting(card)
    catalog = _Catalog([card])
    (
        command,
        events_store,
        states_repo,
        _scheduler,
        _instant,
        uow,
    ) = await _saved_command(sitting=sitting, catalog=catalog)

    with pytest.raises(SittingNotFoundError):
        _ = await command.handle(SittingId.new(), card.id, Grade.GOOD)

    assert events_store.saved == []
    assert states_repo.saved == []
    assert uow.committed is False


async def test_a_card_outside_the_sitting_raises_card_not_in_sitting() -> None:
    member = _reviewable()
    outsider = _reviewable()
    sitting = _open_sitting(member)
    catalog = _Catalog([member, outsider])
    (
        command,
        events_store,
        states_repo,
        _scheduler,
        _instant,
        uow,
    ) = await _saved_command(sitting=sitting, catalog=catalog)

    with pytest.raises(CardNotInSittingError):
        _ = await command.handle(sitting.id, outsider.id, Grade.GOOD)

    assert events_store.saved == []
    assert states_repo.saved == []
    assert uow.committed is False


async def test_a_finished_sitting_raises_already_complete_before_presentable() -> None:
    card = _reviewable()
    sitting = _open_sitting(card)
    prior = _event(card.id, sitting.id, Grade.GOOD)
    catalog = _Catalog([card])
    (
        command,
        events_store,
        states_repo,
        _scheduler,
        _instant,
        uow,
    ) = await _saved_command(sitting=sitting, catalog=catalog, events=(prior,))

    with pytest.raises(SittingAlreadyCompleteError):
        _ = await command.handle(sitting.id, card.id, Grade.EASY)

    assert events_store.saved == []
    assert states_repo.saved == []
    assert uow.committed is False


async def test_a_member_that_is_not_the_seeded_pick_raises_not_presentable() -> None:
    first = _reviewable(front="Alpha")
    second = _reviewable(front="Beta")
    sitting = _open_sitting(first, second)
    catalog = _Catalog([first, second])
    present = sitting.visible(frozenset({first.id, second.id}))
    in_front = sitting.next_card(present, events=[])
    assert in_front is not None
    other = second if in_front == first.id else first
    (
        command,
        events_store,
        states_repo,
        _scheduler,
        _instant,
        uow,
    ) = await _saved_command(sitting=sitting, catalog=catalog)

    with pytest.raises(CardNotPresentableError):
        _ = await command.handle(sitting.id, other.id, Grade.FORGOT)

    assert events_store.saved == []
    assert states_repo.saved == []
    assert uow.committed is False


async def test_a_stale_stamp_rebuilds_previous_from_the_card_log() -> None:
    card = _reviewable(front="Stale memo")
    sitting = _open_sitting(card)
    catalog = _Catalog([card])
    prior_at = datetime(2026, 2, 1, tzinfo=UTC)
    prior = _event(card.id, sitting.id, Grade.FORGOT, reviewed_at=prior_at)
    live = _stamp("live-pin")
    memoized = _state(
        card.id,
        due_at=datetime(2026, 8, 1, tzinfo=UTC),
        stamp=_stamp("old-pin"),
        payload={"memo": "stale"},
    )
    (
        command,
        _events_store,
        _states_repo,
        scheduler,
        instant,
        _uow,
    ) = await _saved_command(
        sitting=sitting,
        catalog=catalog,
        events=(prior,),
        states={card.id: memoized},
        stamp=live,
    )
    expected_previous = SchedulingReplay(_RecordingScheduler(live)).replay(
        card.id, (prior,)
    )

    result = await command.handle(sitting.id, card.id, Grade.GOOD)

    assert expected_previous is not None
    assert scheduler.calls
    grade_call = scheduler.calls[-1]
    assert grade_call[0] == expected_previous
    assert grade_call[0] != memoized
    assert grade_call[1:] == (card.id, Grade.GOOD, instant)
    assert isinstance(result, GradeAppliedDTO)
    assert result.sitting_complete is True
    assert result.next_card_id is None
    assert result.next_front is None
