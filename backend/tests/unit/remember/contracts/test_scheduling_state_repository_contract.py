from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from adapters.out.fsrs.scheduler import FsrsScheduler
from adapters.out.in_memory.remember.scheduling_state_repository import (
    InMemorySchedulingStateRepository,
)
from adapters.out.sqlalchemy.engine import create_session_factory
from adapters.out.sqlalchemy.remember.short_session import (
    ShortSessionSchedulingStateRepository,
)
from domain.remember.ports import SchedulingStateRepository
from domain.remember.scheduling_state import SchedulingState
from domain.remember.value_objects import (
    CardId,
    Grade,
    OpaqueSchedulerState,
    SchedulerAlgorithm,
    SchedulerStamp,
)


@dataclass
class _SchedulingFixture:
    repository: SchedulingStateRepository


@pytest.fixture(
    params=["in_memory", pytest.param("postgres", marks=pytest.mark.postgres)]
)
def scheduling_fixture(request: pytest.FixtureRequest) -> _SchedulingFixture:
    if request.param == "in_memory":  # pyright: ignore[reportAny]
        return _SchedulingFixture(repository=InMemorySchedulingStateRepository())
    engine: AsyncEngine = request.getfixturevalue("engine")  # pyright: ignore[reportAny]
    session_factory = create_session_factory(engine)
    return _SchedulingFixture(
        repository=ShortSessionSchedulingStateRepository(session_factory)
    )


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


async def test_save_then_get_returns_the_saved_state(
    scheduling_fixture: _SchedulingFixture,
) -> None:
    repository = scheduling_fixture.repository
    state = _state(_card_id())

    await repository.save(state)
    result = await repository.get(state.card_id)

    assert result == state


async def test_get_returns_none_for_an_unknown_card_id(
    scheduling_fixture: _SchedulingFixture,
) -> None:
    repository = scheduling_fixture.repository

    result = await repository.get(_card_id())

    assert result is None


async def test_get_many_returns_only_the_ids_it_holds(
    scheduling_fixture: _SchedulingFixture,
) -> None:
    repository = scheduling_fixture.repository
    held = _state(_card_id())
    other = _state(_card_id())
    missing = _card_id()

    await repository.save(held)
    await repository.save(other)
    result = await repository.get_many([held.card_id, missing])

    assert result == {held.card_id: held}
    assert missing not in result
    assert other.card_id not in result


async def test_second_save_for_the_same_card_overwrites(
    scheduling_fixture: _SchedulingFixture,
) -> None:
    repository = scheduling_fixture.repository
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


async def test_scheduling_state_from_fsrs_review_reads_back_equal(
    scheduling_fixture: _SchedulingFixture,
) -> None:
    repository = scheduling_fixture.repository
    scheduler = FsrsScheduler()
    card_id = _card_id()
    reviewed_at = datetime.now(UTC)
    state = scheduler.review(None, card_id, Grade.GOOD, reviewed_at)

    await repository.save(state)
    result = await repository.get(card_id)

    assert result == state
