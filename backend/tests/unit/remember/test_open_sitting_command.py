from collections.abc import Callable
from datetime import timedelta

from integration.support.in_memory_remember import InMemoryRememberComposition

from application.remember.commands.open_sitting import OpenSittingCommand
from application.remember.dto import NothingDueDTO, SittingOpenedDTO, SittingResumedDTO
from domain.remember.value_objects import (
    MIN_RESUME_HORIZON,
    CardId,
    Grade,
    ResumeHorizon,
    ShowingLimit,
    SittingId,
)

from .conftest import OWNER, reviewable, stamp, state


async def test_a_never_reviewed_card_opens_a_sitting_on_its_front(
    make_composition: Callable[..., InMemoryRememberComposition],
) -> None:
    composition = make_composition(showing_limit=ShowingLimit(value=3))
    only = await reviewable(composition, front="Define SYN")
    as_of = composition.clock.now()

    result = await composition.open_sitting().handle(OWNER)

    assert isinstance(result, SittingOpenedDTO)
    assert result.kind == "opened"
    assert result.card_id == only.id.value
    assert result.front == "Define SYN"
    assert result.sitting_complete is False
    sitting = await composition.sittings.get(SittingId(value=result.sitting_id))
    assert sitting is not None
    assert sitting.card_ids == frozenset({only.id})
    assert sitting.opened_at == as_of
    assert sitting.showing_limit == ShowingLimit(value=3)
    assert result.sitting_id == sitting.id.value


async def test_nothing_due_leaves_the_sitting_repository_untouched(
    composition: InMemoryRememberComposition,
) -> None:
    result = await composition.open_sitting().handle(OWNER)

    assert isinstance(result, NothingDueDTO)
    assert result.kind == "nothing_due"
    assert composition.sittings.snapshot() == {}


async def test_reviewable_cards_that_are_not_yet_due_open_no_sitting(
    composition: InMemoryRememberComposition,
) -> None:
    as_of = composition.clock.now()
    live = stamp()
    later = await reviewable(composition)
    await composition.scheduling_states.save(
        state(later.id, due_at=as_of + timedelta(days=30), stamp=live)
    )

    result = await composition.open_sitting().handle(OWNER)

    assert isinstance(result, NothingDueDTO)
    assert composition.sittings.snapshot() == {}


async def test_a_stale_stamp_includes_a_card_whose_due_at_is_still_in_the_future(
    composition: InMemoryRememberComposition,
) -> None:
    as_of = composition.clock.now()
    stale_card = await reviewable(composition, front="Stale front")
    await composition.scheduling_states.save(
        state(
            stale_card.id,
            due_at=as_of + timedelta(days=30),
            stamp=stamp("old-pin"),
        )
    )

    result = await composition.open_sitting().handle(OWNER)

    assert isinstance(result, SittingOpenedDTO)
    assert result.card_id == stale_card.id.value
    assert result.front == "Stale front"
    sitting = await composition.sittings.get(SittingId(value=result.sitting_id))
    assert sitting is not None
    assert sitting.card_ids == frozenset({stale_card.id})


async def test_a_sitting_contains_only_the_cards_that_are_due(
    composition: InMemoryRememberComposition,
) -> None:
    as_of = composition.clock.now()
    live = stamp()
    due = await reviewable(composition, front="Due now")
    later = await reviewable(composition, front="Not yet")
    await composition.scheduling_states.save(
        state(later.id, due_at=as_of + timedelta(days=7), stamp=live)
    )

    result = await composition.open_sitting().handle(OWNER)

    assert isinstance(result, SittingOpenedDTO)
    assert result.card_id == due.id.value
    assert result.front == "Due now"
    sitting = await composition.sittings.get(SittingId(value=result.sitting_id))
    assert sitting is not None
    assert sitting.card_ids == frozenset({due.id})


async def test_a_second_open_while_the_latest_sitting_is_still_offered_returns_resumed(
    composition: InMemoryRememberComposition,
) -> None:
    _ = await reviewable(composition, front="Resume me")

    first = await composition.open_sitting().handle(OWNER)
    second = await composition.open_sitting().handle(OWNER)

    assert isinstance(first, SittingOpenedDTO)
    assert isinstance(second, SittingResumedDTO)
    assert second.kind == "resumed"
    assert second.sitting_id == first.sitting_id


async def test_resuming_an_offered_sitting_writes_no_additional_sitting(
    composition: InMemoryRememberComposition,
) -> None:
    _ = await reviewable(composition)

    _ = await composition.open_sitting().handle(OWNER)
    before = composition.sittings.snapshot()
    _ = await composition.open_sitting().handle(OWNER)
    after = composition.sittings.snapshot()

    assert len(before) == 1
    assert after == before


async def test_a_resumed_sitting_reports_how_many_cards_remain_outstanding(
    composition: InMemoryRememberComposition,
) -> None:
    _ = await reviewable(composition, front="One")
    _ = await reviewable(composition, front="Two")

    _ = await composition.open_sitting().handle(OWNER)
    resumed = await composition.open_sitting().handle(OWNER)

    assert isinstance(resumed, SittingResumedDTO)
    assert resumed.outstanding_count == 2


async def test_resuming_after_one_grade_reports_one_card_still_outstanding(
    composition: InMemoryRememberComposition,
) -> None:
    _ = await reviewable(composition, front="Alpha")
    _ = await reviewable(composition, front="Beta")

    opened = await composition.open_sitting().handle(OWNER)
    assert isinstance(opened, SittingOpenedDTO)
    assert opened.card_id is not None
    _ = await composition.grade_card().handle(
        OWNER,
        SittingId(value=opened.sitting_id),
        CardId(value=opened.card_id),
        Grade.GOOD,
    )

    resumed = await composition.open_sitting().handle(OWNER)

    assert isinstance(resumed, SittingResumedDTO)
    assert resumed.sitting_id == opened.sitting_id
    assert resumed.outstanding_count == 1


async def test_open_sitting_without_resume_horizon_uses_min_resume_horizon(
    composition: InMemoryRememberComposition,
) -> None:
    _ = await reviewable(composition)

    command = OpenSittingCommand(
        uow_factory=composition.unit_of_work,
        catalog=composition.catalog,
        clock=composition.clock,
        showing_limit=composition.showing_limit,
        scheduler=composition.scheduler,
    )
    result = await command.handle(OWNER)

    assert isinstance(result, SittingOpenedDTO)
    sitting = await composition.sittings.get(SittingId(value=result.sitting_id))
    assert sitting is not None
    assert sitting.resume_horizon == ResumeHorizon(value=MIN_RESUME_HORIZON)


async def test_a_resumed_sitting_carries_the_current_card_front(
    composition: InMemoryRememberComposition,
) -> None:
    _ = await reviewable(composition, front="Resume me")

    _ = await composition.open_sitting().handle(OWNER)
    resumed = await composition.open_sitting().handle(OWNER)

    assert isinstance(resumed, SittingResumedDTO)
    assert resumed.front == "Resume me"


async def test_an_opened_sitting_reports_how_many_cards_remain_outstanding(
    composition: InMemoryRememberComposition,
) -> None:
    _ = await reviewable(composition, front="One")
    _ = await reviewable(composition, front="Two")

    opened = await composition.open_sitting().handle(OWNER)

    assert isinstance(opened, SittingOpenedDTO)
    assert opened.outstanding_count == 2
