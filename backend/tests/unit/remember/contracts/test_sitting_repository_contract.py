from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from adapters.out.in_memory.remember.sitting_repository import InMemorySittingRepository
from adapters.out.sqlalchemy.engine import create_session_factory
from domain.remember.ports import SittingRepository
from domain.remember.sitting import Sitting
from domain.remember.value_objects import CardId, ResumeHorizon, ShowingLimit, SittingId
from tests.support.postgres_remember_repositories import CommittingSittingRepository


@dataclass
class _SittingFixture:
    sittings: SittingRepository


@pytest.fixture(
    params=["in_memory", pytest.param("postgres", marks=pytest.mark.postgres)]
)
def sitting_fixture(request: pytest.FixtureRequest) -> _SittingFixture:
    if request.param == "in_memory":  # pyright: ignore[reportAny]
        return _SittingFixture(sittings=InMemorySittingRepository())
    engine: AsyncEngine = request.getfixturevalue("engine")  # pyright: ignore[reportAny]
    session_factory = create_session_factory(engine)
    return _SittingFixture(sittings=CommittingSittingRepository(session_factory))


def _card_id() -> CardId:
    return CardId(value=uuid4())


def _sitting(showing_limit: int = 2) -> Sitting:
    return Sitting.open(
        frozenset({_card_id()}),
        datetime.now(UTC),
        ShowingLimit(value=showing_limit),
    )


async def test_save_then_get_returns_the_sitting_including_showing_limit(
    sitting_fixture: _SittingFixture,
) -> None:
    repository = sitting_fixture.sittings
    sitting = _sitting(showing_limit=3)

    await repository.save(sitting)
    result = await repository.get(sitting.id)

    assert result == sitting
    assert result is not None
    assert result.showing_limit == ShowingLimit(value=3)


async def test_get_returns_none_for_an_unknown_sitting_id(
    sitting_fixture: _SittingFixture,
) -> None:
    repository = sitting_fixture.sittings

    result = await repository.get(SittingId(value=uuid4()))

    assert result is None


async def test_second_save_with_the_same_id_overwrites(
    sitting_fixture: _SittingFixture,
) -> None:
    repository = sitting_fixture.sittings
    original = _sitting(showing_limit=2)
    updated = original.model_copy(update={"showing_limit": ShowingLimit(value=5)})

    await repository.save(original)
    await repository.save(updated)
    result = await repository.get(original.id)

    assert result == updated


async def test_latest_returns_the_sitting_with_the_greatest_opened_at(
    sitting_fixture: _SittingFixture,
) -> None:
    repository = sitting_fixture.sittings
    base = datetime.now(UTC)
    oldest = Sitting.open(
        frozenset({_card_id()}),
        base - timedelta(hours=2),
        ShowingLimit(value=2),
    )
    middle = Sitting.open(
        frozenset({_card_id()}),
        base - timedelta(hours=1),
        ShowingLimit(value=2),
    )
    newest = Sitting.open(
        frozenset({_card_id()}),
        base,
        ShowingLimit(value=2),
    )

    await repository.save(oldest)
    await repository.save(newest)
    await repository.save(middle)
    result = await repository.latest()

    assert result == newest


async def test_second_save_replacing_card_ids_and_resume_horizon_reads_back_equal(
    sitting_fixture: _SittingFixture,
) -> None:
    repository = sitting_fixture.sittings
    original_cards = frozenset({_card_id(), _card_id()})
    replacement_cards = frozenset({_card_id()})
    horizon = ResumeHorizon(value=timedelta(days=3))
    replacement_horizon = ResumeHorizon(value=timedelta(days=5))
    sitting = Sitting.open(
        original_cards,
        datetime.now(UTC),
        ShowingLimit(value=2),
        resume_horizon=horizon,
    )

    await repository.save(sitting)
    updated = sitting.model_copy(
        update={
            "card_ids": replacement_cards,
            "resume_horizon": replacement_horizon,
        }
    )
    await repository.save(updated)
    result = await repository.get(sitting.id)

    assert result == updated
