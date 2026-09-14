import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from adapters.auth.exceptions import TooManyAttemptsError
from adapters.auth.in_memory_attempt_ledger import InMemoryAttemptLedger
from adapters.auth.model import (
    AttemptAction,
    AttemptLimit,
    AttemptLimits,
    AttemptSource,
)
from adapters.auth.ports import AttemptLedger
from adapters.auth.sqlalchemy_attempt_ledger import SqlAlchemyAttemptLedger
from adapters.out.sqlalchemy.engine import create_session_factory


def _limits(max_attempts: int = 2, window: timedelta | None = None) -> AttemptLimits:
    limit = AttemptLimit(
        max_attempts=max_attempts, window=window or timedelta(minutes=15)
    )
    return AttemptLimits(sign_in=limit, registration=limit)


@dataclass
class _LedgerFixture:
    ledger: AttemptLedger
    build: Callable[[AttemptLimits], AttemptLedger]


@pytest.fixture(
    params=["in_memory", pytest.param("postgres", marks=pytest.mark.postgres)]
)
def ledger_fixture(request: pytest.FixtureRequest) -> _LedgerFixture:
    if request.param == "in_memory":  # pyright: ignore[reportAny]

        def build_in_memory(limits: AttemptLimits) -> AttemptLedger:
            return InMemoryAttemptLedger(limits)

        return _LedgerFixture(ledger=build_in_memory(_limits()), build=build_in_memory)

    engine: AsyncEngine = request.getfixturevalue("engine")  # pyright: ignore[reportAny]
    session_factory = create_session_factory(engine)

    def build_postgres(limits: AttemptLimits) -> AttemptLedger:
        return SqlAlchemyAttemptLedger(session_factory, limits)

    return _LedgerFixture(ledger=build_postgres(_limits()), build=build_postgres)


async def test_ensure_allowed_admits_a_source_below_the_limit(
    ledger_fixture: _LedgerFixture,
) -> None:
    source = AttemptSource(value="198.51.100.1")

    await ledger_fixture.ledger.record(AttemptAction.SIGN_IN, source)
    await ledger_fixture.ledger.ensure_allowed(AttemptAction.SIGN_IN, source)


async def test_ensure_allowed_raises_too_many_attempts_once_the_limit_is_reached(
    ledger_fixture: _LedgerFixture,
) -> None:
    source = AttemptSource(value="198.51.100.2")

    await ledger_fixture.ledger.record(AttemptAction.SIGN_IN, source)
    await ledger_fixture.ledger.record(AttemptAction.SIGN_IN, source)

    with pytest.raises(TooManyAttemptsError) as excinfo:
        await ledger_fixture.ledger.ensure_allowed(AttemptAction.SIGN_IN, source)

    assert 890 <= excinfo.value.retry_after_seconds <= 900


async def test_clear_lets_the_source_through_again_after_reaching_the_limit(
    ledger_fixture: _LedgerFixture,
) -> None:
    source = AttemptSource(value="198.51.100.3")

    await ledger_fixture.ledger.record(AttemptAction.SIGN_IN, source)
    await ledger_fixture.ledger.record(AttemptAction.SIGN_IN, source)
    await ledger_fixture.ledger.clear(AttemptAction.SIGN_IN, source)

    await ledger_fixture.ledger.ensure_allowed(AttemptAction.SIGN_IN, source)


async def test_ensure_allowed_is_unaffected_by_another_sources_or_actions_attempts(
    ledger_fixture: _LedgerFixture,
) -> None:
    source = AttemptSource(value="198.51.100.4")
    other_source = AttemptSource(value="198.51.100.5")

    await ledger_fixture.ledger.record(AttemptAction.SIGN_IN, other_source)
    await ledger_fixture.ledger.record(AttemptAction.SIGN_IN, other_source)
    await ledger_fixture.ledger.record(AttemptAction.REGISTRATION, source)
    await ledger_fixture.ledger.record(AttemptAction.REGISTRATION, source)

    await ledger_fixture.ledger.ensure_allowed(AttemptAction.SIGN_IN, source)


async def test_ensure_allowed_admits_a_source_once_its_attempts_age_out_of_the_window(
    ledger_fixture: _LedgerFixture,
) -> None:
    source = AttemptSource(value="198.51.100.6")
    short_window = ledger_fixture.build(
        _limits(max_attempts=1, window=timedelta(milliseconds=1))
    )

    await short_window.record(AttemptAction.SIGN_IN, source)
    await asyncio.sleep(0.05)

    await short_window.ensure_allowed(AttemptAction.SIGN_IN, source)
