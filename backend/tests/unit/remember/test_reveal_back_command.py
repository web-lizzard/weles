from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from integration.support.in_memory_remember import InMemoryRememberComposition

from domain.remember.exceptions import SittingExpiredError
from domain.remember.review_event import ReviewEvent
from domain.remember.value_objects import (
    Grade,
    Graded,
    ResumeHorizon,
    Reveal,
)

from .conftest import (
    clock_after_resume_horizon,
    open_sitting,
    reviewable,
    sitting_past_resume_horizon,
)


def _graded(
    card_id: object,
    sitting_id: object,
    grade: Grade,
) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,  # pyright: ignore[reportArgumentType]
        reviewed_at=datetime.now(UTC),
        payload=Graded(grade=grade),
        sitting_id=sitting_id,  # pyright: ignore[reportArgumentType]
    )


async def test_reveal_persists_a_revealed_payload_review_event_at_the_clock_instant(
    make_composition: Callable[..., InMemoryRememberComposition],
) -> None:
    instant = datetime(2026, 9, 11, 14, 0, tzinfo=UTC)
    composition = make_composition(instant=instant)
    card = await reviewable(composition, front="Front", back="Back text")
    sitting = open_sitting(card)
    await composition.sittings.save(sitting)

    result = await composition.reveal_back().handle(sitting.id, card.id)

    events = await composition.review_events.list_by_card(card.id)
    assert len(events) == 1
    assert events[0].payload == Reveal()
    assert events[0].reviewed_at == instant
    assert events[0].sitting_id == sitting.id
    assert result.back == "Back text"
    assert composition.outbox_store.all() == []


async def test_a_second_reveal_for_the_same_card_appends_no_second_event(
    composition: InMemoryRememberComposition,
) -> None:
    card = await reviewable(composition)
    sitting = open_sitting(card)
    await composition.sittings.save(sitting)
    command = composition.reveal_back()

    first = await command.handle(sitting.id, card.id)
    second = await command.handle(sitting.id, card.id)

    events = await composition.review_events.list_by_card(card.id)
    assert len(events) == 1
    assert events[0].payload == Reveal()
    assert second == first


async def test_a_finished_sitting_still_accepts_reveal_without_guard_outcome(
    composition: InMemoryRememberComposition,
) -> None:
    card = await reviewable(composition, front="Done front", back="Done back")
    sitting = open_sitting(card)
    prior = _graded(card.id, sitting.id, Grade.GOOD)
    await composition.sittings.save(sitting)
    await composition.review_events.save(prior)

    result = await composition.reveal_back().handle(sitting.id, card.id)

    events = await composition.review_events.list_by_card(card.id)
    assert len(events) == 2
    assert events[0].payload == Graded(grade=Grade.GOOD)
    assert events[1].payload == Reveal()
    assert result.back == "Done back"


async def test_an_expired_sitting_leaves_no_review_event_on_reveal(
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
        _ = await composition.reveal_back().handle(sitting.id, card.id)

    assert await composition.review_events.list_by_card(card.id) == []
