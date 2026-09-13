import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.sqlalchemy.engine import create_engine, create_session_factory
from adapters.out.sqlalchemy.shared.outbox.appender import SqlAlchemyOutboxAppender
from adapters.out.sqlalchemy.shared.outbox.claimer import SqlAlchemyOutboxClaimer
from adapters.out.sqlalchemy.shared.outbox.envelope_query import (
    SqlAlchemyOutboxEnvelopeQueryAdapter,
)
from adapters.out.worker.outbox_worker import OutboxWorker
from domain.shared.outbox.model import (
    EnvelopeId,
    EnvelopeStatus,
    EnvelopeType,
    OutboxEnvelope,
)

pytestmark = pytest.mark.postgres

_NOTE_APPROVED = EnvelopeType(name="note_approved")


class _CommittingAppender:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def append(self, envelope: OutboxEnvelope) -> None:
        async with self._session_factory() as session:
            await SqlAlchemyOutboxAppender(session).append(envelope)
            await session.commit()


class _FlakyHandler:
    def __init__(self, envelope_type: EnvelopeType, fail_times: int) -> None:
        self.envelope_type: EnvelopeType = envelope_type
        self._remaining_failures: int = fail_times
        self.handled: list[EnvelopeId] = []

    async def handle(self, envelope: OutboxEnvelope) -> None:
        if self._remaining_failures > 0:
            self._remaining_failures -= 1
            raise RuntimeError("handler failure")
        self.handled.append(envelope.id)


def _fresh_session_factory(
    migrated_database_url: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    fresh_engine = create_engine(migrated_database_url)
    return fresh_engine, create_session_factory(fresh_engine)


async def test_envelope_failed_for_retry_is_reclaimed_intact_through_fresh_engine(
    engine: AsyncEngine,
    migrated_database_url: str,
) -> None:
    session_factory = create_session_factory(engine)
    appender = _CommittingAppender(session_factory)
    claimer = SqlAlchemyOutboxClaimer(session_factory)
    envelope_type = EnvelopeType(name="note_approved", version=2)
    payload: dict[str, object] = {"outer": {"inner": "value"}, "items": [1, 2]}
    envelope = OutboxEnvelope.pending(envelope_type, payload)
    created_at = envelope.created_at
    envelope_id = envelope.id

    await appender.append(envelope)

    claimed = await claimer.claim(envelope_type, limit=1, worker_id="w1")
    assert len(claimed) == 1
    failed = claimed[0]
    failed.fail(max_attempts=5)
    await claimer.fail(failed)

    await engine.dispose()

    fresh_engine, fresh_factory = _fresh_session_factory(migrated_database_url)
    try:
        reclaimed = await SqlAlchemyOutboxClaimer(fresh_factory).claim(
            envelope_type, limit=1, worker_id="w2"
        )
        assert len(reclaimed) == 1
        again = reclaimed[0]
        assert again.id == envelope_id
        assert again.type == envelope_type
        assert again.payload == payload
        assert again.created_at == created_at
        assert again.attempts == 2
    finally:
        await fresh_engine.dispose()


async def test_claimed_envelope_lists_as_processing_through_fresh_engine_query(
    engine: AsyncEngine,
    migrated_database_url: str,
) -> None:
    session_factory = create_session_factory(engine)
    appender = _CommittingAppender(session_factory)
    claimer = SqlAlchemyOutboxClaimer(session_factory)
    envelope = OutboxEnvelope.pending(_NOTE_APPROVED, {"note_id": "x"})
    await appender.append(envelope)

    claimed = await claimer.claim(_NOTE_APPROVED, limit=1, worker_id="worker-42")
    assert len(claimed) == 1
    claimed_envelope = claimed[0]

    await engine.dispose()

    fresh_engine, fresh_factory = _fresh_session_factory(migrated_database_url)
    try:
        listed = await SqlAlchemyOutboxEnvelopeQueryAdapter(
            fresh_factory
        ).list_envelopes()
        assert len(listed) == 1
        dto = listed[0]
        assert dto.id == envelope.id.value
        assert dto.status == EnvelopeStatus.PROCESSING.value
        assert dto.claimed_by == "worker-42"
        assert dto.claimed_at == claimed_envelope.claimed_at
    finally:
        await fresh_engine.dispose()


async def test_query_lists_each_envelope_with_type_string_and_current_status(
    engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(engine)
    appender = _CommittingAppender(session_factory)
    claimer = SqlAlchemyOutboxClaimer(session_factory)
    query = SqlAlchemyOutboxEnvelopeQueryAdapter(session_factory)
    type_processing = EnvelopeType(name="note_approved")
    type_pending = EnvelopeType(name="other_event", version=3)
    processing_envelope = OutboxEnvelope.pending(type_processing, {})
    pending_envelope = OutboxEnvelope.pending(type_pending, {})
    await appender.append(processing_envelope)
    await appender.append(pending_envelope)
    _ = await claimer.claim(type_processing, limit=1, worker_id="w1")

    listed = await query.list_envelopes()
    by_id = {dto.id: dto for dto in listed}

    assert by_id[processing_envelope.id.value].type == "note_approved@1"
    assert by_id[processing_envelope.id.value].status == EnvelopeStatus.PROCESSING.value
    assert by_id[pending_envelope.id.value].type == "other_event@3"
    assert by_id[pending_envelope.id.value].status == EnvelopeStatus.PENDING.value


async def test_worker_on_postgres_retries_then_dead_letters_at_max_attempts(
    engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(engine)
    appender = _CommittingAppender(session_factory)
    claimer = SqlAlchemyOutboxClaimer(session_factory)
    query = SqlAlchemyOutboxEnvelopeQueryAdapter(session_factory)
    envelope = OutboxEnvelope.pending(_NOTE_APPROVED, {"n": 1})
    await appender.append(envelope)
    handler = _FlakyHandler(_NOTE_APPROVED, fail_times=10)
    worker = OutboxWorker(
        claimer, [handler], worker_id="w1", batch_size=10, max_attempts=3
    )

    first_acked = await worker.run_once()
    assert first_acked == 0
    after_first = await query.list_envelopes()
    assert after_first[0].status == EnvelopeStatus.PENDING.value
    assert after_first[0].attempts == 1

    for _ in range(2):
        acked = await worker.run_once()
        assert acked == 0

    after_max = await query.list_envelopes()
    assert after_max[0].status == EnvelopeStatus.FAILED.value
    assert after_max[0].attempts == 3
