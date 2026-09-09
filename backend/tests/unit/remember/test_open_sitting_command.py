from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from application.remember.commands.open_sitting import OpenSittingCommand
from application.remember.dto import NothingDueDTO, SittingOpenedDTO
from domain.remember.ports import ReviewableCard
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
    front: str = "What is TCP?",
    back: str = "A handshake.",
) -> ReviewableCard:
    return ReviewableCard(id=card_id or _card_id(), front=front, back=back)


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
) -> SchedulingState:
    return SchedulingState(
        card_id=card_id,
        due_at=due_at,
        scheduler_state=OpaqueSchedulerState(payload={}),
        stamp=stamp,
    )


class _Clock:
    def __init__(self, instant: datetime) -> None:
        self._instant: datetime = instant

    def now(self) -> datetime:
        return self._instant


class _Scheduler:
    def __init__(self, stamp: SchedulerStamp) -> None:
        self._stamp: SchedulerStamp = stamp

    def stamp(self) -> SchedulerStamp:
        return self._stamp

    def review(
        self,
        previous: SchedulingState | None,
        card_id: CardId,
        grade: Grade,
        reviewed_at: datetime,
    ) -> SchedulingState:
        del previous, card_id, grade, reviewed_at
        raise AssertionError("opening a sitting must not call Scheduler.review")


class _Catalog:
    def __init__(self, cards: Sequence[ReviewableCard]) -> None:
        self._cards: tuple[ReviewableCard, ...] = tuple(cards)

    async def list_reviewable(self) -> Sequence[ReviewableCard]:
        return self._cards

    async def get_reviewable(self, card_id: CardId) -> ReviewableCard | None:
        return next((card for card in self._cards if card.id == card_id), None)


class _SittingRepository:
    def __init__(self) -> None:
        self._sittings: dict[SittingId, Sitting] = {}
        self.saved: list[Sitting] = []

    async def save(self, sitting: Sitting) -> None:
        self.saved.append(sitting)
        self._sittings[sitting.id] = sitting

    async def get(self, sitting_id: SittingId) -> Sitting | None:
        return self._sittings.get(sitting_id)


class _SchedulingStateRepository:
    def __init__(self, states: dict[CardId, SchedulingState] | None = None) -> None:
        self._states: dict[CardId, SchedulingState] = dict(states or {})

    async def save(self, state: SchedulingState) -> None:
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


class _ReviewEventStore:
    async def save(self, event: ReviewEvent) -> None:
        del event

    async def list_by_card(self, card_id: CardId) -> Sequence[ReviewEvent]:
        del card_id
        return ()

    async def list_by_sitting(self, sitting_id: SittingId) -> Sequence[ReviewEvent]:
        del sitting_id
        return ()


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
    cards: Sequence[ReviewableCard],
    states: dict[CardId, SchedulingState] | None = None,
    as_of: datetime | None = None,
    stamp: SchedulerStamp | None = None,
    showing_limit: ShowingLimit | None = None,
) -> tuple[OpenSittingCommand, _SittingRepository, datetime]:
    instant = as_of or datetime.now(UTC)
    sittings = _SittingRepository()
    scheduling_states = _SchedulingStateRepository(states)
    review_events = _ReviewEventStore()

    def uow_factory() -> _UnitOfWork:
        return _UnitOfWork(sittings, scheduling_states, review_events)

    command = OpenSittingCommand(
        uow_factory,
        _Catalog(cards),
        _Clock(instant),
        showing_limit or ShowingLimit(value=2),
        _Scheduler(stamp or _stamp()),  # pyright: ignore[reportCallIssue]
    )
    return command, sittings, instant


async def test_a_never_reviewed_card_opens_a_sitting_on_its_front() -> None:
    only = _reviewable(front="Define SYN")
    command, sittings, as_of = _command(
        cards=[only], showing_limit=ShowingLimit(value=3)
    )

    result = await command.handle()

    assert isinstance(result, SittingOpenedDTO)
    assert result.kind == "opened"
    assert result.card_id == only.id.value
    assert result.front == "Define SYN"
    assert result.sitting_complete is False
    assert len(sittings.saved) == 1
    sitting = sittings.saved[0]
    assert sitting.card_ids == frozenset({only.id})
    assert sitting.opened_at == as_of
    assert sitting.showing_limit == ShowingLimit(value=3)
    assert result.sitting_id == sitting.id.value


async def test_nothing_due_leaves_the_sitting_repository_untouched() -> None:
    command, sittings, _as_of = _command(cards=[])

    result = await command.handle()

    assert isinstance(result, NothingDueDTO)
    assert result.kind == "nothing_due"
    assert sittings.saved == []


async def test_reviewable_cards_that_are_not_yet_due_open_no_sitting() -> None:
    as_of = datetime.now(UTC)
    later = _reviewable()
    live = _stamp()
    command, sittings, _ = _command(
        cards=[later],
        states={
            later.id: _state(later.id, due_at=as_of + timedelta(days=30), stamp=live)
        },
        as_of=as_of,
        stamp=live,
    )

    result = await command.handle()

    assert isinstance(result, NothingDueDTO)
    assert sittings.saved == []


async def test_a_stale_stamp_includes_a_card_whose_due_at_is_still_in_the_future() -> (
    None
):
    as_of = datetime.now(UTC)
    stale_card = _reviewable(front="Stale front")
    command, sittings, _ = _command(
        cards=[stale_card],
        states={
            stale_card.id: _state(
                stale_card.id,
                due_at=as_of + timedelta(days=30),
                stamp=_stamp("old-pin"),
            )
        },
        as_of=as_of,
        stamp=_stamp("live-pin"),
    )

    result = await command.handle()

    assert isinstance(result, SittingOpenedDTO)
    assert result.card_id == stale_card.id.value
    assert result.front == "Stale front"
    assert sittings.saved[0].card_ids == frozenset({stale_card.id})


async def test_a_sitting_contains_only_the_cards_that_are_due() -> None:
    as_of = datetime.now(UTC)
    live = _stamp()
    due = _reviewable(front="Due now")
    later = _reviewable(front="Not yet")
    command, sittings, _ = _command(
        cards=[due, later],
        states={
            later.id: _state(later.id, due_at=as_of + timedelta(days=7), stamp=live),
        },
        as_of=as_of,
        stamp=live,
    )

    result = await command.handle()

    assert isinstance(result, SittingOpenedDTO)
    assert result.card_id == due.id.value
    assert result.front == "Due now"
    assert sittings.saved[0].card_ids == frozenset({due.id})
