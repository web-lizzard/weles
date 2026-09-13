import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.claimer import InMemoryOutboxClaimer
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from adapters.out.sqlalchemy.engine import create_session_factory
from adapters.out.sqlalchemy.shared.outbox.appender import SqlAlchemyOutboxAppender
from adapters.out.sqlalchemy.shared.outbox.claimer import SqlAlchemyOutboxClaimer
from domain.shared.outbox.model import EnvelopeStatus, EnvelopeType, OutboxEnvelope
from domain.shared.outbox.ports import OutboxAppender, OutboxClaimer

_NOTE_APPROVED = EnvelopeType(name="note_approved")
_NOTE_APPROVED_V2 = EnvelopeType(name="note_approved", version=2)
_OTHER_EVENT = EnvelopeType(name="other_event")


class _CommittingAppender:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def append(self, envelope: OutboxEnvelope) -> None:
        async with self._session_factory() as session:
            await SqlAlchemyOutboxAppender(session).append(envelope)
            await session.commit()


def _pending(envelope_type: EnvelopeType = _NOTE_APPROVED) -> OutboxEnvelope:
    return OutboxEnvelope.pending(envelope_type, {"note_id": "abc"})


@pytest.fixture(
    params=["in_memory", pytest.param("postgres", marks=pytest.mark.postgres)]
)
def ports(request: pytest.FixtureRequest) -> tuple[OutboxAppender, OutboxClaimer]:
    if request.param == "in_memory":  # pyright: ignore[reportAny]
        store = InMemoryOutboxStore()
        return InMemoryOutboxAppender(store), InMemoryOutboxClaimer(store)
    engine: AsyncEngine = request.getfixturevalue("engine")  # pyright: ignore[reportAny]
    session_factory = create_session_factory(engine)
    return (
        _CommittingAppender(session_factory),
        SqlAlchemyOutboxClaimer(session_factory),
    )


async def test_claim_stamps_claimed_by_with_worker(
    ports: tuple[OutboxAppender, OutboxClaimer],
) -> None:
    appender, claimer = ports
    for _ in range(2):
        await appender.append(_pending())

    claimed = await claimer.claim(_NOTE_APPROVED, limit=10, worker_id="w1")

    assert len(claimed) == 2
    assert all(envelope.claimed_by == "w1" for envelope in claimed)
    assert all(envelope.status == EnvelopeStatus.PROCESSING for envelope in claimed)


async def test_claim_returns_at_most_limit_pending_envelopes_of_matching_type(
    ports: tuple[OutboxAppender, OutboxClaimer],
) -> None:
    appender, claimer = ports
    matching = [_pending() for _ in range(3)]
    other = _pending(_OTHER_EVENT)
    for envelope in [*matching, other]:
        await appender.append(envelope)

    claimed = await claimer.claim(_NOTE_APPROVED, limit=2, worker_id="w1")

    claimed_ids = {envelope.id for envelope in claimed}
    matching_ids = {envelope.id for envelope in matching}
    assert len(claimed) == 2
    assert claimed_ids <= matching_ids


async def test_concurrent_claims_return_disjoint_envelopes(
    ports: tuple[OutboxAppender, OutboxClaimer],
) -> None:
    appender, claimer = ports
    envelopes = [_pending() for _ in range(4)]
    for envelope in envelopes:
        await appender.append(envelope)

    first, second = await asyncio.gather(
        claimer.claim(_NOTE_APPROVED, limit=10, worker_id="w1"),
        claimer.claim(_NOTE_APPROVED, limit=10, worker_id="w2"),
    )

    first_ids = {envelope.id for envelope in first}
    second_ids = {envelope.id for envelope in second}
    assert first_ids.isdisjoint(second_ids)
    assert first_ids | second_ids == {envelope.id for envelope in envelopes}


async def test_claim_does_not_cross_match_envelope_type_versions(
    ports: tuple[OutboxAppender, OutboxClaimer],
) -> None:
    appender, claimer = ports
    await appender.append(_pending(_NOTE_APPROVED_V2))

    claimed = await claimer.claim(_NOTE_APPROVED, limit=10, worker_id="w1")

    assert claimed == []


async def test_retryable_fail_returns_to_pending_and_ack_does_not(
    ports: tuple[OutboxAppender, OutboxClaimer],
) -> None:
    appender, claimer = ports
    to_ack = _pending()
    to_retry = _pending()
    to_dead_letter = _pending()
    for envelope in (to_ack, to_retry, to_dead_letter):
        await appender.append(envelope)

    claimed = await claimer.claim(_NOTE_APPROVED, limit=3, worker_id="w1")
    by_id = {envelope.id: envelope for envelope in claimed}

    by_id[to_ack.id].consume()
    await claimer.ack(by_id[to_ack.id])

    by_id[to_retry.id].fail(max_attempts=3)
    await claimer.fail(by_id[to_retry.id])

    by_id[to_dead_letter.id].fail(max_attempts=1)
    await claimer.fail(by_id[to_dead_letter.id])

    again = await claimer.claim(_NOTE_APPROVED, limit=10, worker_id="w2")

    assert [envelope.id for envelope in again] == [to_retry.id]
