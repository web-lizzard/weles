"""Step definitions for remember-flow acceptance scenarios."""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest
from pytest_bdd import given, parsers, then, when

from application.remember.commands.grade_card import GradeCardCommand
from application.remember.commands.open_sitting import OpenSittingCommand
from application.remember.dto import (
    GradeAppliedDTO,
    NothingDueDTO,
    PresentedCardDTO,
    RevealedCardDTO,
    SittingOpenedDTO,
)
from application.remember.ports import UnitOfWork
from application.remember.queries.current_card import CurrentCardQuery
from application.remember.queries.reveal_back import RevealBackQuery
from domain.remember.ports import (
    ReviewableCard,
    ReviewEventStore,
    SchedulingStateRepository,
    SittingRepository,
)
from domain.remember.review_event import ReviewEvent
from domain.remember.scheduling_state import SchedulingState, card_is_due
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


class _FixedClock:
    def __init__(self, moment: datetime) -> None:
        self._moment: datetime = moment

    def now(self) -> datetime:
        return self._moment


class _FakeReviewCatalog:
    def __init__(self) -> None:
        self._cards: dict[CardId, ReviewableCard] = {}

    def add(self, card: ReviewableCard) -> None:
        self._cards[card.id] = card

    async def list_reviewable(self) -> Sequence[ReviewableCard]:
        return list(self._cards.values())

    async def get_reviewable(self, card_id: CardId) -> ReviewableCard | None:
        return self._cards.get(card_id)


class _InMemorySittingRepository:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Sitting] = {}

    async def save(self, sitting: Sitting) -> None:
        self._by_id[sitting.id.value] = sitting

    async def get(self, sitting_id: SittingId) -> Sitting | None:
        return self._by_id.get(sitting_id.value)

    def all(self) -> list[Sitting]:
        return list(self._by_id.values())


class _InMemoryReviewEventStore:
    def __init__(self) -> None:
        self._events: list[ReviewEvent] = []

    async def save(self, event: ReviewEvent) -> None:
        self._events.append(event)

    async def list_by_card(self, card_id: CardId) -> Sequence[ReviewEvent]:
        return sorted(
            [event for event in self._events if event.card_id == card_id],
            key=lambda event: event.reviewed_at,
        )

    async def list_by_sitting(self, sitting_id: SittingId) -> Sequence[ReviewEvent]:
        return sorted(
            [event for event in self._events if event.sitting_id == sitting_id],
            key=lambda event: event.reviewed_at,
        )


class _InMemorySchedulingStateRepository:
    def __init__(self) -> None:
        self._by_card: dict[CardId, SchedulingState] = {}

    async def save(self, state: SchedulingState) -> None:
        self._by_card[state.card_id] = state

    async def get(self, card_id: CardId) -> SchedulingState | None:
        return self._by_card.get(card_id)

    async def get_many(
        self, card_ids: Sequence[CardId]
    ) -> dict[CardId, SchedulingState]:
        return {
            card_id: state
            for card_id in card_ids
            if (state := self._by_card.get(card_id))
        }


class _FakeUnitOfWork:
    def __init__(
        self,
        sittings: _InMemorySittingRepository,
        review_events: _InMemoryReviewEventStore,
        scheduling_states: _InMemorySchedulingStateRepository,
    ) -> None:
        self.sittings: SittingRepository = sittings
        self.review_events: ReviewEventStore = review_events
        self.scheduling_states: SchedulingStateRepository = scheduling_states

    async def __aenter__(self) -> "_FakeUnitOfWork":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def commit(self) -> None:
        return None


class _FakeScheduler:
    _STAMP: SchedulerStamp = SchedulerStamp(
        algorithm=SchedulerAlgorithm.FSRS, parameter_version="test"
    )

    def stamp(self) -> SchedulerStamp:
        return self._STAMP

    def review(
        self,
        previous: SchedulingState | None,
        card_id: CardId,
        grade: Grade,
        reviewed_at: datetime,
    ) -> SchedulingState:
        prior_interval = timedelta(days=0)
        if previous is not None:
            prior_interval = previous.due_at - reviewed_at
        multiplier = {
            Grade.FORGOT: 1,
            Grade.HARD: 2,
            Grade.GOOD: 4,
            Grade.EASY: 8,
        }[grade]
        base_days = 1 if prior_interval <= timedelta(days=0) else prior_interval.days
        next_days = max(1, base_days * multiplier)
        due_at = reviewed_at + timedelta(days=next_days)
        return SchedulingState(
            card_id=card_id,
            due_at=due_at,
            scheduler_state=OpaqueSchedulerState(payload={"step": next_days}),
            stamp=self._STAMP,
        )


@dataclass
class RememberFlowContext:
    clock: _FixedClock
    catalog: _FakeReviewCatalog
    sittings: _InMemorySittingRepository
    events: _InMemoryReviewEventStore
    scheduling_states: _InMemorySchedulingStateRepository
    scheduler: _FakeScheduler
    showing_limit: ShowingLimit
    open_sitting: OpenSittingCommand
    grade_card: GradeCardCommand
    reveal_back: RevealBackQuery
    current_card: CurrentCardQuery
    cards_by_label: dict[str, ReviewableCard] = field(default_factory=dict)
    last_open_result: SittingOpenedDTO | NothingDueDTO | None = None
    last_presented: PresentedCardDTO | None = None
    last_reveal_result: RevealedCardDTO | None = None
    last_grade_result: GradeAppliedDTO | None = None
    sitting_id: SittingId | None = None
    current_card_id: CardId | None = None
    graded_card_id: CardId | None = None
    second_good_grade_due_at: datetime | None = None


@pytest.fixture
def remember_flow_context() -> RememberFlowContext:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
    clock = _FixedClock(now)
    catalog = _FakeReviewCatalog()
    sittings = _InMemorySittingRepository()
    events = _InMemoryReviewEventStore()
    scheduling_states = _InMemorySchedulingStateRepository()

    def uow_factory() -> UnitOfWork:
        return cast(
            UnitOfWork,
            cast(
                object,
                _FakeUnitOfWork(sittings, events, scheduling_states),
            ),
        )

    showing_limit = ShowingLimit(value=2)
    scheduler = _FakeScheduler()
    sitting_repo = cast(SittingRepository, cast(object, sittings))
    event_store = cast(ReviewEventStore, cast(object, events))
    return RememberFlowContext(
        clock=clock,
        catalog=catalog,
        sittings=sittings,
        events=events,
        scheduling_states=scheduling_states,
        scheduler=scheduler,
        showing_limit=showing_limit,
        open_sitting=OpenSittingCommand(
            uow_factory=uow_factory,
            catalog=catalog,
            clock=clock,
            showing_limit=showing_limit,
        ),
        grade_card=GradeCardCommand(
            uow_factory=uow_factory,
            catalog=catalog,
            scheduler=scheduler,
            clock=clock,
        ),
        reveal_back=RevealBackQuery(sittings=sitting_repo, catalog=catalog),
        current_card=CurrentCardQuery(
            sittings=sitting_repo, events=event_store, catalog=catalog
        ),
    )


def _card(
    label: str,
    front: str | None = None,
    back: str | None = None,
) -> ReviewableCard:
    slug = label.replace(" ", "-")
    return ReviewableCard(
        id=CardId(value=uuid4()),
        front=front or f"Front for {slug}",
        back=back or f"Back for {slug}",
    )


def _mark_due(
    context: RememberFlowContext, card_id: CardId, due_at: datetime | None = None
) -> None:
    reviewed_at = context.clock.now() - timedelta(days=1)
    due = due_at or reviewed_at
    state = context.scheduler.review(None, card_id, Grade.GOOD, reviewed_at)
    due_state = state.model_copy(update={"due_at": due})
    asyncio.run(context.scheduling_states.save(due_state))


def _mark_not_due(context: RememberFlowContext, card_id: CardId) -> None:
    future = context.clock.now() + timedelta(days=30)
    reviewed_at = context.clock.now() - timedelta(days=1)
    state = context.scheduler.review(None, card_id, Grade.GOOD, reviewed_at)
    not_due_state = state.model_copy(update={"due_at": future})
    asyncio.run(context.scheduling_states.save(not_due_state))


@given("a remember review backend")
def remember_review_backend(_remember_flow_context: RememberFlowContext) -> None:
    return None


@given(
    parsers.parse(
        'the catalog has a due card "{label}" and a not-due card "{not_due_label}"'
    )
)
def catalog_has_due_and_not_due(
    remember_flow_context: RememberFlowContext, label: str, not_due_label: str
) -> None:
    due_card = _card(label)
    not_due_card = _card(not_due_label)
    remember_flow_context.catalog.add(due_card)
    remember_flow_context.catalog.add(not_due_card)
    remember_flow_context.cards_by_label[label] = due_card
    remember_flow_context.cards_by_label[not_due_label] = not_due_card
    _mark_due(remember_flow_context, due_card.id)
    _mark_not_due(remember_flow_context, not_due_card.id)


@given("the catalog has no due cards")
def catalog_has_no_due_cards(remember_flow_context: RememberFlowContext) -> None:
    card = _card("future-only")
    remember_flow_context.catalog.add(card)
    remember_flow_context.cards_by_label["future-only"] = card
    _mark_not_due(remember_flow_context, card.id)


@given(parsers.parse('the catalog has a due card "{label}"'))
def catalog_has_due_card(
    remember_flow_context: RememberFlowContext, label: str
) -> None:
    card = _card(label)
    remember_flow_context.catalog.add(card)
    remember_flow_context.cards_by_label[label] = card
    _mark_due(remember_flow_context, card.id)


@given(parsers.parse('the catalog has due cards "{first}", "{second}", and "{third}"'))
def catalog_has_three_due_cards(
    remember_flow_context: RememberFlowContext,
    first: str,
    second: str,
    third: str,
) -> None:
    for label in (first, second, third):
        card = _card(label)
        remember_flow_context.catalog.add(card)
        remember_flow_context.cards_by_label[label] = card
        _mark_due(remember_flow_context, card.id)


@given(
    parsers.parse(
        'the catalog has a due card "{label}" with front "{front}" and back "{back}"'
    )
)
def catalog_has_due_card_with_content(
    remember_flow_context: RememberFlowContext,
    label: str,
    front: str,
    back: str,
) -> None:
    card = _card(label, front=front, back=back)
    remember_flow_context.catalog.add(card)
    remember_flow_context.cards_by_label[label] = card
    _mark_due(remember_flow_context, card.id)


@given("the card has two prior good grades in its history")
def card_has_two_prior_good_grades(remember_flow_context: RememberFlowContext) -> None:
    card = next(iter(remember_flow_context.cards_by_label.values()))
    sitting_one = SittingId.new()
    sitting_two = SittingId.new()
    first_at = remember_flow_context.clock.now() - timedelta(days=10)
    second_at = remember_flow_context.clock.now() - timedelta(days=5)
    for sitting_id, reviewed_at in (
        (sitting_one, first_at),
        (sitting_two, second_at),
    ):
        event = ReviewEvent(
            card_id=card.id,
            reviewed_at=reviewed_at,
            grade=Grade.GOOD,
            sitting_id=sitting_id,
        )
        asyncio.run(remember_flow_context.events.save(event))
        previous = asyncio.run(remember_flow_context.scheduling_states.get(card.id))
        state = remember_flow_context.scheduler.review(
            previous, card.id, Grade.GOOD, reviewed_at
        )
        asyncio.run(remember_flow_context.scheduling_states.save(state))
        if sitting_id == sitting_two:
            remember_flow_context.second_good_grade_due_at = state.due_at
    _mark_due(remember_flow_context, card.id, due_at=remember_flow_context.clock.now())


@given("the user has started a review")
def user_has_started_review(remember_flow_context: RememberFlowContext) -> None:
    result = asyncio.run(remember_flow_context.open_sitting.handle())
    assert isinstance(result, SittingOpenedDTO)
    remember_flow_context.last_open_result = result
    remember_flow_context.sitting_id = SittingId(value=result.sitting_id)
    remember_flow_context.current_card_id = CardId(value=result.card_id)
    remember_flow_context.last_presented = result


@given("the user has revealed the current card's back")
def user_has_revealed_current_back(remember_flow_context: RememberFlowContext) -> None:
    assert remember_flow_context.sitting_id is not None
    assert remember_flow_context.current_card_id is not None
    result = asyncio.run(
        remember_flow_context.reveal_back.handle(
            remember_flow_context.sitting_id,
            remember_flow_context.current_card_id,
        )
    )
    remember_flow_context.last_reveal_result = result


@when("the user starts a review")
def user_starts_review(remember_flow_context: RememberFlowContext) -> None:
    result = asyncio.run(remember_flow_context.open_sitting.handle())
    remember_flow_context.last_open_result = result
    if isinstance(result, SittingOpenedDTO):
        remember_flow_context.sitting_id = SittingId(value=result.sitting_id)
        remember_flow_context.current_card_id = CardId(value=result.card_id)
        remember_flow_context.last_presented = result


@when("the user reveals the current card's back")
def user_reveals_current_back(remember_flow_context: RememberFlowContext) -> None:
    assert remember_flow_context.sitting_id is not None
    assert remember_flow_context.current_card_id is not None
    result = asyncio.run(
        remember_flow_context.reveal_back.handle(
            remember_flow_context.sitting_id,
            remember_flow_context.current_card_id,
        )
    )
    remember_flow_context.last_reveal_result = result


@when(parsers.parse('the user grades the current card as "{grade_name}"'))
def user_grades_current_card(
    remember_flow_context: RememberFlowContext, grade_name: str
) -> None:
    assert remember_flow_context.sitting_id is not None
    assert remember_flow_context.current_card_id is not None
    remember_flow_context.graded_card_id = remember_flow_context.current_card_id
    grade = Grade(grade_name.lower())
    result = asyncio.run(
        remember_flow_context.grade_card.handle(
            remember_flow_context.sitting_id,
            remember_flow_context.current_card_id,
            grade,
        )
    )
    remember_flow_context.last_grade_result = result
    if result.next_card_id is not None:
        remember_flow_context.current_card_id = CardId(value=result.next_card_id)
        remember_flow_context.last_presented = PresentedCardDTO(
            sitting_id=result.sitting_id,
            card_id=result.next_card_id,
            front=result.next_front or "",
            sitting_complete=result.sitting_complete,
        )


@then("the opened sitting contains every due card")
def opened_sitting_contains_every_due_card(
    remember_flow_context: RememberFlowContext,
) -> None:
    assert isinstance(remember_flow_context.last_open_result, SittingOpenedDTO)
    sitting = asyncio.run(
        remember_flow_context.sittings.get(
            SittingId(value=remember_flow_context.last_open_result.sitting_id)
        )
    )
    assert sitting is not None
    due_ids = {
        card.id
        for card in asyncio.run(remember_flow_context.catalog.list_reviewable())
        if card_is_due(
            asyncio.run(remember_flow_context.scheduling_states.get(card.id)),
            remember_flow_context.clock.now(),
        )
    }
    assert due_ids.issubset(sitting.card_ids)


@then("the opened sitting excludes cards that are not due")
def opened_sitting_excludes_not_due_cards(
    remember_flow_context: RememberFlowContext,
) -> None:
    assert isinstance(remember_flow_context.last_open_result, SittingOpenedDTO)
    sitting = asyncio.run(
        remember_flow_context.sittings.get(
            SittingId(value=remember_flow_context.last_open_result.sitting_id)
        )
    )
    assert sitting is not None
    not_due_ids = {
        card.id
        for card in asyncio.run(remember_flow_context.catalog.list_reviewable())
        if not card_is_due(
            asyncio.run(remember_flow_context.scheduling_states.get(card.id)),
            remember_flow_context.clock.now(),
        )
    }
    assert not_due_ids.isdisjoint(sitting.card_ids)


@then("the user is told nothing is due")
def user_is_told_nothing_is_due(remember_flow_context: RememberFlowContext) -> None:
    assert isinstance(remember_flow_context.last_open_result, NothingDueDTO)


@then("no sitting was created")
def no_sitting_was_created(remember_flow_context: RememberFlowContext) -> None:
    assert remember_flow_context.sittings.all() == []


@then("the current card shows only the front")
def current_card_shows_only_front(remember_flow_context: RememberFlowContext) -> None:
    assert remember_flow_context.last_presented is not None
    assert remember_flow_context.last_presented.front.strip() != ""
    assert remember_flow_context.last_reveal_result is None


@then("the current card shows the back")
def current_card_shows_back(remember_flow_context: RememberFlowContext) -> None:
    assert remember_flow_context.last_reveal_result is not None
    assert remember_flow_context.last_reveal_result.back.strip() != ""


@then("exactly one card is in front of the user")
def exactly_one_card_in_front(remember_flow_context: RememberFlowContext) -> None:
    assert remember_flow_context.last_presented is not None
    assert remember_flow_context.last_presented.card_id is not None


@then("the grade is recorded for that card")
def grade_is_recorded_for_card(remember_flow_context: RememberFlowContext) -> None:
    assert remember_flow_context.sitting_id is not None
    assert remember_flow_context.current_card_id is not None
    events = asyncio.run(
        remember_flow_context.events.list_by_sitting(remember_flow_context.sitting_id)
    )
    assert any(
        event.card_id == remember_flow_context.current_card_id for event in events
    )


@then("the card has a scheduled next due date")
def card_has_scheduled_next_due(remember_flow_context: RememberFlowContext) -> None:
    card = next(iter(remember_flow_context.cards_by_label.values()))
    state = asyncio.run(remember_flow_context.scheduling_states.get(card.id))
    assert state is not None
    assert state.due_at > remember_flow_context.clock.now()


@then("the next due date is farther out than after the second good grade")
def next_due_is_farther_than_second_good(
    remember_flow_context: RememberFlowContext,
) -> None:
    card = next(iter(remember_flow_context.cards_by_label.values()))
    state = asyncio.run(remember_flow_context.scheduling_states.get(card.id))
    assert state is not None
    assert remember_flow_context.second_good_grade_due_at is not None
    assert state.due_at > remember_flow_context.second_good_grade_due_at


@then(parsers.parse('the card still shows front "{front}" and back "{back}"'))
def card_still_shows_same_content(
    remember_flow_context: RememberFlowContext, front: str, back: str
) -> None:
    card = next(iter(remember_flow_context.cards_by_label.values()))
    reviewable = asyncio.run(remember_flow_context.catalog.get_reviewable(card.id))
    assert reviewable is not None
    assert reviewable.front == front
    assert reviewable.back == back


@then("the same card is presented again before the sitting ends")
def same_card_presented_again_before_end(
    remember_flow_context: RememberFlowContext,
) -> None:
    assert remember_flow_context.last_grade_result is not None
    assert remember_flow_context.graded_card_id is not None
    assert remember_flow_context.last_grade_result.sitting_complete is False
    assert (
        remember_flow_context.last_grade_result.next_card_id
        == remember_flow_context.graded_card_id.value
    )
