from collections.abc import Callable
from datetime import timedelta

from integration.support.in_memory_remember import InMemoryRememberComposition

from application.remember.dto import NothingDueDTO, SittingOpenedDTO
from domain.remember.value_objects import ShowingLimit, SittingId

from .conftest import reviewable, stamp, state


async def test_a_never_reviewed_card_opens_a_sitting_on_its_front(
    make_composition: Callable[..., InMemoryRememberComposition],
) -> None:
    composition = make_composition(showing_limit=ShowingLimit(value=3))
    only = await reviewable(composition, front="Define SYN")
    as_of = composition.clock.now()

    result = await composition.open_sitting().handle()

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
    result = await composition.open_sitting().handle()

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

    result = await composition.open_sitting().handle()

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

    result = await composition.open_sitting().handle()

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

    result = await composition.open_sitting().handle()

    assert isinstance(result, SittingOpenedDTO)
    assert result.card_id == due.id.value
    assert result.front == "Due now"
    sitting = await composition.sittings.get(SittingId(value=result.sitting_id))
    assert sitting is not None
    assert sitting.card_ids == frozenset({due.id})
