from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import pytest

from adapters.out.in_memory.remember.scheduling_state_repository import (
    InMemorySchedulingStateRepository,
)
from domain.remember.ports import SchedulingStateRepository
from domain.remember.scheduling_state import SchedulingState
from domain.remember.value_objects import (
    CardId,
    OpaqueSchedulerState,
    SchedulerAlgorithm,
    SchedulerStamp,
)

_IMPLEMENTATIONS: list[Callable[[], SchedulingStateRepository]] = [
    cast(Callable[[], SchedulingStateRepository], InMemorySchedulingStateRepository),
]


def _card_id() -> CardId:
    return CardId(value=uuid4())


def _state(
    card_id: CardId,
    *,
    due_at: datetime | None = None,
    parameter_version: str = "fsrs-6.3.2-defaults",
) -> SchedulingState:
    return SchedulingState(
        card_id=card_id,
        due_at=due_at or datetime.now(UTC),
        scheduler_state=OpaqueSchedulerState(payload={"stability": 1.0}),
        stamp=SchedulerStamp(
            algorithm=SchedulerAlgorithm.FSRS,
            parameter_version=parameter_version,
        ),
    )


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_save_then_get_returns_the_saved_state(
    make_repository: Callable[[], SchedulingStateRepository],
) -> None:
    repository = make_repository()
    state = _state(_card_id())

    await repository.save(state)
    result = await repository.get(state.card_id)

    assert result == state


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_get_returns_none_for_an_unknown_card_id(
    make_repository: Callable[[], SchedulingStateRepository],
) -> None:
    repository = make_repository()

    result = await repository.get(_card_id())

    assert result is None


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_get_many_returns_only_the_ids_it_holds(
    make_repository: Callable[[], SchedulingStateRepository],
) -> None:
    repository = make_repository()
    held = _state(_card_id())
    other = _state(_card_id())
    missing = _card_id()

    await repository.save(held)
    await repository.save(other)
    result = await repository.get_many([held.card_id, missing])

    assert result == {held.card_id: held}
    assert missing not in result
    assert other.card_id not in result


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_second_save_for_the_same_card_overwrites(
    make_repository: Callable[[], SchedulingStateRepository],
) -> None:
    repository = make_repository()
    card_id = _card_id()
    original = _state(card_id, due_at=datetime.now(UTC))
    updated = _state(
        card_id,
        due_at=datetime.now(UTC) + timedelta(days=3),
        parameter_version="fsrs-6.3.2-defaults",
    )

    await repository.save(original)
    await repository.save(updated)
    result = await repository.get(card_id)

    assert result == updated
