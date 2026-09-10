"""Step definitions for remember-flow acceptance scenarios."""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from integration.support.in_memory_remember import InMemoryRememberComposition
from pytest_bdd import given, parsers, then, when

from application.remember.dto import (
    GradeAppliedDTO,
    NothingDueDTO,
    PresentedCardDTO,
    RevealedCardDTO,
    SittingOpenedDTO,
)
from domain.distill.card import Card
from domain.distill.note import Note
from domain.distill.value_objects import (
    Anchor,
    CardSide,
    Discard,
    DiscardReason,
    DistillationStatus,
    NoteContent,
    NoteId,
    SessionId,
    TopicSnapshot,
)
from domain.distill.value_objects import (
    CardId as DistillCardId,
)
from domain.remember.ports import ReviewableCard
from domain.remember.review_event import ReviewEvent
from domain.remember.scheduling_state import SchedulingState, card_is_due
from domain.remember.value_objects import (
    CardId,
    Grade,
    OpaqueSchedulerState,
    SchedulerAlgorithm,
    SchedulerStamp,
    SittingId,
)


class _FixedClock:
    """Drives the collaborator into a state the real clock cannot reach on demand."""

    def __init__(self, moment: datetime) -> None:
        self._moment: datetime = moment

    def now(self) -> datetime:
        return self._moment


@dataclass
class RememberFlowContext:
    clock: _FixedClock
    composition: InMemoryRememberComposition
    cards_by_label: dict[str, ReviewableCard] = field(default_factory=dict)
    distill_cards_by_label: dict[str, Card] = field(default_factory=dict)
    last_open_result: SittingOpenedDTO | NothingDueDTO | None = None
    last_presented: PresentedCardDTO | None = None
    last_reveal_result: RevealedCardDTO | None = None
    last_grade_result: GradeAppliedDTO | None = None
    sitting_id: SittingId | None = None
    current_card_id: CardId | None = None
    graded_card_id: CardId | None = None
    second_good_grade_due_at: datetime | None = None
    current_card_reads: list[PresentedCardDTO] = field(default_factory=list)
    live_membership: frozenset[CardId] | None = None
    prior_sitting_id: SittingId | None = None


@pytest.fixture
def remember_flow_context() -> RememberFlowContext:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
    clock = _FixedClock(now)
    composition = InMemoryRememberComposition.create(clock=clock)
    return RememberFlowContext(clock=clock, composition=composition)


def _card(
    context: RememberFlowContext,
    label: str,
    front: str | None = None,
    back: str | None = None,
) -> ReviewableCard:
    slug = label.replace(" ", "-")
    front_text = front or f"Front for {slug}"
    back_text = back or f"Back for {slug}"
    now = datetime.now(UTC)
    note = Note(
        id=NoteId(value=uuid4()),
        session_id=SessionId(value=uuid4()),
        topic=TopicSnapshot(id=uuid4(), label=slug),
        content=NoteContent(value=f"Note content backing the card {slug}."),
        tags=[],
        distillation_status=DistillationStatus.READY,
        approved_at=now,
        created_at=now,
        updated_at=now,
    )
    card = Card(
        id=DistillCardId(value=uuid4()),
        note_id=note.id,
        front=CardSide(value=front_text),
        back=CardSide(value=back_text),
        anchor=Anchor(quote=f"Anchor backing the card {slug}."),
        discard=None,
        created_at=now,
    )
    asyncio.run(context.composition.notes.save(note))
    asyncio.run(context.composition.cards.save(card))
    context.distill_cards_by_label[label] = card
    reviewable = ReviewableCard(
        id=CardId(value=card.id.value), front=front_text, back=back_text
    )
    context.cards_by_label[label] = reviewable
    return reviewable


def _mark_due(
    context: RememberFlowContext, card_id: CardId, due_at: datetime | None = None
) -> None:
    reviewed_at = context.clock.now() - timedelta(days=1)
    due = due_at or reviewed_at
    state = context.composition.scheduler.review(None, card_id, Grade.GOOD, reviewed_at)
    due_state = state.model_copy(update={"due_at": due})
    asyncio.run(context.composition.scheduling_states.save(due_state))


def _mark_not_due(context: RememberFlowContext, card_id: CardId) -> None:
    future = context.clock.now() + timedelta(days=30)
    reviewed_at = context.clock.now() - timedelta(days=1)
    state = context.composition.scheduler.review(None, card_id, Grade.GOOD, reviewed_at)
    not_due_state = state.model_copy(update={"due_at": future})
    asyncio.run(context.composition.scheduling_states.save(not_due_state))


@given("a remember review backend")
def remember_review_backend(remember_flow_context: RememberFlowContext) -> None:
    _ = remember_flow_context


@given(
    parsers.parse(
        'the catalog has a due card "{label}" and a not-due card "{not_due_label}"'
    )
)
def catalog_has_due_and_not_due(
    remember_flow_context: RememberFlowContext, label: str, not_due_label: str
) -> None:
    due_card = _card(remember_flow_context, label)
    not_due_card = _card(remember_flow_context, not_due_label)
    _mark_due(remember_flow_context, due_card.id)
    _mark_not_due(remember_flow_context, not_due_card.id)


@given("the catalog has no due cards")
def catalog_has_no_due_cards(remember_flow_context: RememberFlowContext) -> None:
    card = _card(remember_flow_context, "future-only")
    _mark_not_due(remember_flow_context, card.id)


@given(parsers.parse('the catalog has a due card "{label}"'))
def catalog_has_due_card(
    remember_flow_context: RememberFlowContext, label: str
) -> None:
    card = _card(remember_flow_context, label)
    _mark_due(remember_flow_context, card.id)


@given(parsers.parse('the catalog has due cards "{first}" and "{second}"'))
def catalog_has_two_due_cards(
    remember_flow_context: RememberFlowContext,
    first: str,
    second: str,
) -> None:
    for label in (first, second):
        card = _card(remember_flow_context, label)
        _mark_due(remember_flow_context, card.id)


@given(parsers.parse('the catalog has due cards "{first}", "{second}", and "{third}"'))
def catalog_has_three_due_cards(
    remember_flow_context: RememberFlowContext,
    first: str,
    second: str,
    third: str,
) -> None:
    for label in (first, second, third):
        card = _card(remember_flow_context, label)
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
    card = _card(remember_flow_context, label, front=front, back=back)
    _mark_due(remember_flow_context, card.id)


@given(
    parsers.parse(
        'the catalog has a due card "{label}" with a stale memoized scheduler stamp'
    )
)
def catalog_has_due_card_with_stale_stamp(
    remember_flow_context: RememberFlowContext, label: str
) -> None:
    card = _card(remember_flow_context, label)
    stale_stamp = SchedulerStamp(
        algorithm=SchedulerAlgorithm.FSRS,
        parameter_version="stale-version",
    )
    future = remember_flow_context.clock.now() + timedelta(days=30)
    asyncio.run(
        remember_flow_context.composition.scheduling_states.save(
            SchedulingState(
                card_id=card.id,
                due_at=future,
                scheduler_state=OpaqueSchedulerState(payload={"step": 30}),
                stamp=stale_stamp,
            )
        )
    )


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
        asyncio.run(remember_flow_context.composition.review_events.save(event))
        previous = asyncio.run(
            remember_flow_context.composition.scheduling_states.get(card.id)
        )
        state = remember_flow_context.composition.scheduler.review(
            previous, card.id, Grade.GOOD, reviewed_at
        )
        asyncio.run(remember_flow_context.composition.scheduling_states.save(state))
        if sitting_id == sitting_two:
            remember_flow_context.second_good_grade_due_at = state.due_at
    due_state = state.model_copy(update={"due_at": remember_flow_context.clock.now()})
    asyncio.run(remember_flow_context.composition.scheduling_states.save(due_state))


@given("the user has started a review")
def user_has_started_review(remember_flow_context: RememberFlowContext) -> None:
    result = asyncio.run(remember_flow_context.composition.open_sitting().handle())
    assert isinstance(result, SittingOpenedDTO)
    remember_flow_context.last_open_result = result
    remember_flow_context.sitting_id = SittingId(value=result.sitting_id)
    assert result.card_id is not None
    remember_flow_context.current_card_id = CardId(value=result.card_id)
    remember_flow_context.last_presented = result


@given("the user has revealed the current card's back")
@when("the user has revealed the current card's back")
def user_has_revealed_current_back(remember_flow_context: RememberFlowContext) -> None:
    assert remember_flow_context.sitting_id is not None
    assert remember_flow_context.current_card_id is not None
    result = asyncio.run(
        remember_flow_context.composition.reveal_back().handle(
            remember_flow_context.sitting_id,
            remember_flow_context.current_card_id,
        )
    )
    remember_flow_context.last_reveal_result = result


@given(parsers.parse('the card "{label}" is the one in front'))
def card_is_the_one_in_front(
    remember_flow_context: RememberFlowContext, label: str
) -> None:
    # The seeded draw over equally-eligible cards is a coin flip (R4-F3):
    # read which card it picked and swap labels rather than asserting the pick.
    assert remember_flow_context.current_card_id is not None
    drawn = remember_flow_context.current_card_id
    if remember_flow_context.cards_by_label[label].id == drawn:
        return
    other_label = next(
        candidate
        for candidate, card in remember_flow_context.cards_by_label.items()
        if card.id == drawn
    )
    labels = remember_flow_context.cards_by_label
    labels[label], labels[other_label] = labels[other_label], labels[label]


@when("the user starts a review")
@when("the user starts a review again")
def user_starts_review(remember_flow_context: RememberFlowContext) -> None:
    if remember_flow_context.sitting_id is not None:
        remember_flow_context.prior_sitting_id = remember_flow_context.sitting_id
    result = asyncio.run(remember_flow_context.composition.open_sitting().handle())
    remember_flow_context.last_open_result = result
    if isinstance(result, SittingOpenedDTO):
        remember_flow_context.sitting_id = SittingId(value=result.sitting_id)
        assert result.card_id is not None
        remember_flow_context.current_card_id = CardId(value=result.card_id)
        remember_flow_context.last_presented = result


@when("the user reveals the current card's back")
def user_reveals_current_back(remember_flow_context: RememberFlowContext) -> None:
    assert remember_flow_context.sitting_id is not None
    assert remember_flow_context.current_card_id is not None
    result = asyncio.run(
        remember_flow_context.composition.reveal_back().handle(
            remember_flow_context.sitting_id,
            remember_flow_context.current_card_id,
        )
    )
    remember_flow_context.last_reveal_result = result


@given(parsers.parse('the user grades the current card as "{grade_name}"'))
@when(parsers.parse('the user grades the current card as "{grade_name}"'))
def user_grades_current_card(
    remember_flow_context: RememberFlowContext, grade_name: str
) -> None:
    assert remember_flow_context.sitting_id is not None
    assert remember_flow_context.current_card_id is not None
    remember_flow_context.graded_card_id = remember_flow_context.current_card_id
    grade = Grade(grade_name.lower())
    result = asyncio.run(
        remember_flow_context.composition.grade_card().handle(
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


@when(parsers.parse('the card "{label}" is discarded from the catalog'))
def card_is_discarded_from_catalog(
    remember_flow_context: RememberFlowContext, label: str
) -> None:
    card = remember_flow_context.distill_cards_by_label[label]
    discarded = card.model_copy(
        update={
            "discard": Discard(
                reason=DiscardReason.USER_AUDIT,
                detail=None,
                discarded_at=remember_flow_context.clock.now(),
            )
        }
    )
    asyncio.run(remember_flow_context.composition.cards.save(discarded))
    remember_flow_context.distill_cards_by_label[label] = discarded


@when("the sitting's live membership is read")
def sitting_live_membership_is_read(
    remember_flow_context: RememberFlowContext,
) -> None:
    assert remember_flow_context.sitting_id is not None
    sitting = asyncio.run(
        remember_flow_context.composition.sittings.get(remember_flow_context.sitting_id)
    )
    assert sitting is not None
    live_ids = frozenset(
        card.id
        for card in asyncio.run(
            remember_flow_context.composition.catalog.list_reviewable()
        )
    )
    remember_flow_context.live_membership = sitting.visible(live_ids)


@when("the user reads the current card")
@when("the user reads the current card again")
def user_reads_current_card(remember_flow_context: RememberFlowContext) -> None:
    assert remember_flow_context.sitting_id is not None
    result = asyncio.run(
        remember_flow_context.composition.current_card().handle(
            remember_flow_context.sitting_id
        )
    )
    remember_flow_context.current_card_reads.append(result)
    remember_flow_context.last_presented = result
    assert result.card_id is not None
    remember_flow_context.current_card_id = CardId(value=result.card_id)


@when(parsers.parse('the card "{label}" still has a next due date in the past'))
def card_still_has_past_due_date(
    remember_flow_context: RememberFlowContext, label: str
) -> None:
    card = remember_flow_context.cards_by_label[label]
    past = remember_flow_context.clock.now() - timedelta(hours=1)
    state = asyncio.run(
        remember_flow_context.composition.scheduling_states.get(card.id)
    )
    assert state is not None
    asyncio.run(
        remember_flow_context.composition.scheduling_states.save(
            state.model_copy(update={"due_at": past})
        )
    )


@then("the opened sitting contains every due card")
def opened_sitting_contains_every_due_card(
    remember_flow_context: RememberFlowContext,
) -> None:
    assert isinstance(remember_flow_context.last_open_result, SittingOpenedDTO)
    sitting = asyncio.run(
        remember_flow_context.composition.sittings.get(
            SittingId(value=remember_flow_context.last_open_result.sitting_id)
        )
    )
    assert sitting is not None
    due_ids = {
        card.id
        for card in asyncio.run(
            remember_flow_context.composition.catalog.list_reviewable()
        )
        if card_is_due(
            asyncio.run(
                remember_flow_context.composition.scheduling_states.get(card.id)
            ),
            remember_flow_context.clock.now(),
            remember_flow_context.composition.scheduler.stamp(),
        )
    }
    assert due_ids.issubset(sitting.card_ids)


@then("the opened sitting excludes cards that are not due")
def opened_sitting_excludes_not_due_cards(
    remember_flow_context: RememberFlowContext,
) -> None:
    assert isinstance(remember_flow_context.last_open_result, SittingOpenedDTO)
    sitting = asyncio.run(
        remember_flow_context.composition.sittings.get(
            SittingId(value=remember_flow_context.last_open_result.sitting_id)
        )
    )
    assert sitting is not None
    not_due_ids = {
        card.id
        for card in asyncio.run(
            remember_flow_context.composition.catalog.list_reviewable()
        )
        if not card_is_due(
            asyncio.run(
                remember_flow_context.composition.scheduling_states.get(card.id)
            ),
            remember_flow_context.clock.now(),
            remember_flow_context.composition.scheduler.stamp(),
        )
    }
    assert not_due_ids.isdisjoint(sitting.card_ids)


@then(parsers.parse('the opened sitting contains the due card "{label}"'))
def opened_sitting_contains_named_due_card(
    remember_flow_context: RememberFlowContext, label: str
) -> None:
    assert isinstance(remember_flow_context.last_open_result, SittingOpenedDTO)
    card = remember_flow_context.cards_by_label[label]
    sitting = asyncio.run(
        remember_flow_context.composition.sittings.get(
            SittingId(value=remember_flow_context.last_open_result.sitting_id)
        )
    )
    assert sitting is not None
    assert card.id in sitting.card_ids


@then(parsers.parse('the live set excludes the card "{label}"'))
def live_set_excludes_named_card(
    remember_flow_context: RememberFlowContext, label: str
) -> None:
    assert remember_flow_context.live_membership is not None
    card = remember_flow_context.cards_by_label[label]
    assert card.id not in remember_flow_context.live_membership


@then(parsers.parse('the sitting\'s stored set still contains the card "{label}"'))
def stored_set_still_contains_named_card(
    remember_flow_context: RememberFlowContext, label: str
) -> None:
    assert remember_flow_context.sitting_id is not None
    sitting = asyncio.run(
        remember_flow_context.composition.sittings.get(remember_flow_context.sitting_id)
    )
    assert sitting is not None
    card = remember_flow_context.cards_by_label[label]
    assert card.id in sitting.card_ids


@then("both readings show the same card")
def both_readings_show_same_card(remember_flow_context: RememberFlowContext) -> None:
    assert len(remember_flow_context.current_card_reads) == 2
    first, second = remember_flow_context.current_card_reads
    assert first.card_id == second.card_id


@then("the next card shown is not the card just graded")
def next_card_is_not_the_one_just_graded(
    remember_flow_context: RememberFlowContext,
) -> None:
    assert remember_flow_context.last_grade_result is not None
    assert remember_flow_context.graded_card_id is not None
    assert remember_flow_context.last_grade_result.next_card_id is not None
    assert (
        remember_flow_context.last_grade_result.next_card_id
        != remember_flow_context.graded_card_id.value
    )


@then(
    parsers.parse('the grade from the prior sitting is recorded for the card "{label}"')
)
def grade_from_prior_sitting_is_recorded(
    remember_flow_context: RememberFlowContext, label: str
) -> None:
    assert remember_flow_context.prior_sitting_id is not None
    card = remember_flow_context.cards_by_label[label]
    events = asyncio.run(
        remember_flow_context.composition.review_events.list_by_sitting(
            remember_flow_context.prior_sitting_id
        )
    )
    assert any(event.card_id == card.id for event in events)


@then("the sitting ends without presenting that card again")
def sitting_ends_without_presenting_that_card_again(
    remember_flow_context: RememberFlowContext,
) -> None:
    assert remember_flow_context.last_grade_result is not None
    assert remember_flow_context.last_grade_result.sitting_complete is True
    assert remember_flow_context.last_grade_result.next_card_id is None


@then(
    parsers.parse('the card "{label}" is not presented again before the sitting ends')
)
def named_card_not_presented_again_before_sitting_ends(
    remember_flow_context: RememberFlowContext, label: str
) -> None:
    card = remember_flow_context.cards_by_label[label]
    assert remember_flow_context.last_grade_result is not None
    next_card_id = remember_flow_context.last_grade_result.next_card_id
    if next_card_id is not None:
        assert next_card_id != card.id.value


@then("the user is told nothing is due")
def user_is_told_nothing_is_due(remember_flow_context: RememberFlowContext) -> None:
    assert isinstance(remember_flow_context.last_open_result, NothingDueDTO)


@then("no sitting was created")
def no_sitting_was_created(remember_flow_context: RememberFlowContext) -> None:
    assert remember_flow_context.composition.sittings.snapshot() == {}


@then("the current card shows only the front")
def current_card_shows_only_front(remember_flow_context: RememberFlowContext) -> None:
    assert remember_flow_context.last_presented is not None
    front = remember_flow_context.last_presented.front
    assert front is not None
    assert front.strip() != ""
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
        remember_flow_context.composition.review_events.list_by_sitting(
            remember_flow_context.sitting_id
        )
    )
    assert any(
        event.card_id == remember_flow_context.current_card_id for event in events
    )


@then("the card has a scheduled next due date")
def card_has_scheduled_next_due(remember_flow_context: RememberFlowContext) -> None:
    card = next(iter(remember_flow_context.cards_by_label.values()))
    state = asyncio.run(
        remember_flow_context.composition.scheduling_states.get(card.id)
    )
    assert state is not None
    assert state.due_at > remember_flow_context.clock.now()


@then("the next due date is farther out than after the second good grade")
def next_due_is_farther_than_second_good(
    remember_flow_context: RememberFlowContext,
) -> None:
    card = next(iter(remember_flow_context.cards_by_label.values()))
    state = asyncio.run(
        remember_flow_context.composition.scheduling_states.get(card.id)
    )
    assert state is not None
    assert remember_flow_context.second_good_grade_due_at is not None
    assert state.due_at > remember_flow_context.second_good_grade_due_at


@then(parsers.parse('the card still shows front "{front}" and back "{back}"'))
def card_still_shows_same_content(
    remember_flow_context: RememberFlowContext, front: str, back: str
) -> None:
    card = next(iter(remember_flow_context.cards_by_label.values()))
    reviewable = asyncio.run(
        remember_flow_context.composition.catalog.get_reviewable(card.id)
    )
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
