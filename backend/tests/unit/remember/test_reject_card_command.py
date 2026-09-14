from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from integration.support.in_memory_remember import InMemoryRememberComposition

from application.remember.commands.reject_card import RejectCardCommand
from domain.remember.exceptions import (
    CardNotInSittingError,
    CardNotPresentableError,
    SittingAlreadyCompleteError,
    SittingExpiredError,
)
from domain.remember.outbox import CARD_REJECTED, CardRejectedPayload
from domain.remember.review_event import ReviewEvent
from domain.remember.value_objects import (
    Grade,
    Graded,
    Rejection,
    ResumeHorizon,
    SittingId,
)
from domain.shared.outbox.model import OutboxEnvelope

from .conftest import (
    OWNER,
    clock_after_resume_horizon,
    open_sitting,
    reviewable,
    sitting_past_resume_horizon,
    stamp,
    state,
)


def _event(
    card_id: object,
    sitting_id: SittingId,
    grade: Grade,
    *,
    reviewed_at: datetime | None = None,
) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,  # pyright: ignore[reportArgumentType]
        reviewed_at=reviewed_at or datetime.now(UTC),
        payload=Graded(grade=grade),
        sitting_id=sitting_id,
    )


async def _assert_no_rejection_side_effects(
    composition: InMemoryRememberComposition,
    card_id: object,
) -> None:
    assert await composition.review_events.list_by_card(card_id) == []  # pyright: ignore[reportArgumentType]
    assert composition.outbox_store.all() == []
    assert await composition.scheduling_states.get(card_id) is None  # pyright: ignore[reportArgumentType]


async def test_a_sitting_past_its_horizon_refuses_rejection_before_any_write(
    make_composition: Callable[..., InMemoryRememberComposition],
) -> None:
    opened_at = datetime(2026, 4, 10, 9, 0, tzinfo=UTC)
    horizon = ResumeHorizon(value=timedelta(hours=1))
    composition = make_composition(instant=clock_after_resume_horizon(opened_at))
    card = await reviewable(composition)
    sitting = sitting_past_resume_horizon(
        card, opened_at=opened_at, resume_horizon=horizon
    )
    await composition.sittings.save(sitting)

    with pytest.raises(SittingExpiredError):
        await composition.reject_card().handle(OWNER, sitting.id, card.id)

    await _assert_no_rejection_side_effects(composition, card.id)


async def test_a_card_outside_the_sitting_refuses_rejection(
    composition: InMemoryRememberComposition,
) -> None:
    member = await reviewable(composition)
    outsider = await reviewable(composition)
    sitting = open_sitting(member)
    await composition.sittings.save(sitting)

    with pytest.raises(CardNotInSittingError):
        await composition.reject_card().handle(OWNER, sitting.id, outsider.id)

    await _assert_no_rejection_side_effects(composition, outsider.id)


async def test_a_finished_sitting_refuses_rejection_before_presentable(
    composition: InMemoryRememberComposition,
) -> None:
    card = await reviewable(composition)
    sitting = open_sitting(card)
    prior = _event(card.id, sitting.id, Grade.GOOD)
    await composition.sittings.save(sitting)
    await composition.review_events.save(prior)

    with pytest.raises(SittingAlreadyCompleteError):
        await composition.reject_card().handle(OWNER, sitting.id, card.id)

    assert await composition.review_events.list_by_card(card.id) == [prior]
    assert composition.outbox_store.all() == []
    assert await composition.scheduling_states.get(card.id) is None


async def test_a_member_that_is_not_the_seeded_pick_refuses_rejection(
    composition: InMemoryRememberComposition,
) -> None:
    first = await reviewable(composition, front="Alpha")
    second = await reviewable(composition, front="Beta")
    sitting = open_sitting(first, second)
    present = sitting.visible(frozenset({first.id, second.id}))
    in_front = sitting.next_card(present, events=[])
    assert in_front is not None
    other = second if in_front == first.id else first
    await composition.sittings.save(sitting)

    with pytest.raises(CardNotPresentableError):
        await composition.reject_card().handle(OWNER, sitting.id, other.id)

    await _assert_no_rejection_side_effects(composition, other.id)


async def test_rejection_persists_a_rejected_event_and_card_rejected_envelope_together(
    make_composition: Callable[..., InMemoryRememberComposition],
) -> None:
    instant = datetime(2026, 9, 1, 12, 30, tzinfo=UTC)
    composition = make_composition(instant=instant)
    card = await reviewable(composition)
    sitting = open_sitting(card)
    await composition.sittings.save(sitting)

    await composition.reject_card().handle(OWNER, sitting.id, card.id)

    events = await composition.review_events.list_by_card(card.id)
    assert len(events) == 1
    assert events[0].payload == Rejection()
    assert events[0].reviewed_at == instant
    assert events[0].sitting_id == sitting.id

    envelopes = composition.outbox_store.all()
    assert len(envelopes) == 1
    assert envelopes[0].type == CARD_REJECTED
    assert envelopes[0].payload == CardRejectedPayload(
        card_id=card.id.value, rejected_at=instant
    ).model_dump(mode="json")


async def test_rejection_leaves_scheduling_state_untouched_when_one_already_exists(
    composition: InMemoryRememberComposition,
) -> None:
    card = await reviewable(composition)
    sitting = open_sitting(card)
    memoized = state(
        card.id,
        due_at=datetime(2026, 8, 1, tzinfo=UTC),
        stamp=stamp(),
        payload={"stability": 2.5},
    )
    await composition.sittings.save(sitting)
    await composition.scheduling_states.save(memoized)

    await composition.reject_card().handle(OWNER, sitting.id, card.id)

    events = await composition.review_events.list_by_card(card.id)
    assert len(events) == 1
    assert events[0].payload == Rejection()
    assert await composition.scheduling_states.get(card.id) == memoized


class _RaisingOutboxAppender:
    """Forces append failure to prove a failed rejection leaves no partial write."""

    async def append(self, envelope: OutboxEnvelope) -> None:
        del envelope
        raise RuntimeError("outbox unavailable")


async def test_a_failing_outbox_append_leaves_no_review_event_or_envelope(
    composition: InMemoryRememberComposition,
) -> None:
    card = await reviewable(composition)
    sitting = open_sitting(card)
    await composition.sittings.save(sitting)
    original_uow_factory = composition.unit_of_work

    def uow_with_raising_outbox(owner: object) -> object:
        uow = original_uow_factory(owner)  # pyright: ignore[reportArgumentType]
        uow.outbox = _RaisingOutboxAppender()
        return uow

    command = RejectCardCommand(
        uow_factory=uow_with_raising_outbox,  # pyright: ignore[reportArgumentType]
        catalog=composition.catalog,
        clock=composition.clock,
    )

    with pytest.raises(RuntimeError):
        await command.handle(OWNER, sitting.id, card.id)

    await _assert_no_rejection_side_effects(composition, card.id)
    assert await composition.sittings.get(sitting.id) == sitting
