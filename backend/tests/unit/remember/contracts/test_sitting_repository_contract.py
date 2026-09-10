from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import pytest

from adapters.out.in_memory.remember.sitting_repository import InMemorySittingRepository
from domain.remember.ports import SittingRepository
from domain.remember.sitting import Sitting
from domain.remember.value_objects import CardId, ShowingLimit, SittingId

_IMPLEMENTATIONS: list[Callable[[], SittingRepository]] = [
    cast(Callable[[], SittingRepository], InMemorySittingRepository),
]


def _card_id() -> CardId:
    return CardId(value=uuid4())


def _sitting(showing_limit: int = 2) -> Sitting:
    return Sitting.open(
        frozenset({_card_id()}),
        datetime.now(UTC),
        ShowingLimit(value=showing_limit),
    )


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_save_then_get_returns_the_sitting_including_showing_limit(
    make_repository: Callable[[], SittingRepository],
) -> None:
    repository = make_repository()
    sitting = _sitting(showing_limit=3)

    await repository.save(sitting)
    result = await repository.get(sitting.id)

    assert result == sitting
    assert result is not None
    assert result.showing_limit == ShowingLimit(value=3)


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_get_returns_none_for_an_unknown_sitting_id(
    make_repository: Callable[[], SittingRepository],
) -> None:
    repository = make_repository()

    result = await repository.get(SittingId(value=uuid4()))

    assert result is None


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_second_save_with_the_same_id_overwrites(
    make_repository: Callable[[], SittingRepository],
) -> None:
    repository = make_repository()
    original = _sitting(showing_limit=2)
    updated = original.model_copy(update={"showing_limit": ShowingLimit(value=5)})

    await repository.save(original)
    await repository.save(updated)
    result = await repository.get(original.id)

    assert result == updated
