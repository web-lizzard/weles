from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from integration.support.in_memory_remember import InMemoryRememberComposition

from application.remember.dto import PresentedCardDTO
from domain.remember.exceptions import SittingExpiredError, SittingNotFoundError
from domain.remember.review_event import ReviewEvent
from domain.remember.value_objects import Grade, ResumeHorizon, SittingId

from .conftest import (
    clock_after_resume_horizon,
    open_sitting,
    reviewable,
    sitting_past_resume_horizon,
)


def _event(card_id: object, sitting_id: SittingId, grade: Grade) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,  # pyright: ignore[reportArgumentType]
        reviewed_at=datetime.now(UTC),
        grade=grade,
        sitting_id=sitting_id,
    )


async def test_a_sitting_past_its_horizon_raises_expired_on_current_card(
    make_composition: Callable[..., InMemoryRememberComposition],
) -> None:
    opened_at = datetime(2026, 4, 10, 9, 0, tzinfo=UTC)
    horizon = ResumeHorizon(value=timedelta(hours=1))
    composition = make_composition(instant=clock_after_resume_horizon(opened_at))
    card = await reviewable(composition, front="Past horizon")
    sitting = sitting_past_resume_horizon(
        card, opened_at=opened_at, resume_horizon=horizon
    )
    await composition.sittings.save(sitting)

    with pytest.raises(SittingExpiredError):
        _ = await composition.current_card().handle(sitting.id)


async def test_the_current_card_is_the_next_draw_from_the_sitting_log(
    composition: InMemoryRememberComposition,
) -> None:
    shown = await reviewable(composition, front="Shown already")
    unshown = await reviewable(composition, front="Still waiting")
    sitting = open_sitting(shown, unshown)
    events = (_event(shown.id, sitting.id, Grade.FORGOT),)
    await composition.sittings.save(sitting)
    await composition.review_events.save(events[0])
    expected = sitting.next_card(
        sitting.visible(frozenset({shown.id, unshown.id})), events
    )
    assert expected is not None

    result = await composition.current_card().handle(sitting.id)

    assert isinstance(result, PresentedCardDTO)
    assert result.sitting_id == sitting.id.value
    assert result.card_id == expected.value
    assert result.front == unshown.front
    assert result.sitting_complete is False


async def test_an_unknown_sitting_raises_sitting_not_found(
    composition: InMemoryRememberComposition,
) -> None:
    with pytest.raises(SittingNotFoundError):
        _ = await composition.current_card().handle(SittingId.new())


async def test_two_consecutive_reads_return_the_same_card(
    composition: InMemoryRememberComposition,
) -> None:
    card = await reviewable(composition, front="Stable pick")
    sitting = open_sitting(card)
    await composition.sittings.save(sitting)

    first = await composition.current_card().handle(sitting.id)
    second = await composition.current_card().handle(sitting.id)

    assert first.card_id == second.card_id
    assert first.front == second.front == "Stable pick"
    assert first.sitting_complete is False
    assert second.sitting_complete is False


async def test_a_discarded_member_is_excluded_from_the_draw(
    composition: InMemoryRememberComposition,
) -> None:
    kept = await reviewable(composition, front="Still reviewable")
    dropped = await reviewable(composition, front="Discarded elsewhere", discarded=True)
    sitting = open_sitting(kept, dropped)
    await composition.sittings.save(sitting)

    result = await composition.current_card().handle(sitting.id)

    assert result.card_id == kept.id.value
    assert result.front == "Still reviewable"
    assert result.sitting_complete is False


async def test_a_finished_sitting_reports_completion_through_the_dto(
    composition: InMemoryRememberComposition,
) -> None:
    """Phase 6 contract: sitting_complete comes from is_finished on the DTO."""
    card = await reviewable(composition, front="Finished by grade")
    sitting = open_sitting(card)
    event = _event(card.id, sitting.id, Grade.GOOD)
    await composition.sittings.save(sitting)
    await composition.review_events.save(event)

    result = await composition.current_card().handle(sitting.id)

    assert isinstance(result, PresentedCardDTO)
    assert result.sitting_complete is True
