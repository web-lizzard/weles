import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from adapters.out.sqlalchemy.engine import create_session_factory
from adapters.out.sqlalchemy.shared.outbox.appender import SqlAlchemyOutboxAppender
from adapters.out.sqlalchemy.shared.outbox.claimer import SqlAlchemyOutboxClaimer
from domain.shared.outbox.model import EnvelopeType, OutboxEnvelope

pytestmark = pytest.mark.postgres

_NOTE_APPROVED = EnvelopeType(name="note_approved")


def _pending() -> OutboxEnvelope:
    return OutboxEnvelope.pending(_NOTE_APPROVED, {"note_id": "abc"})


async def test_envelope_appended_in_a_rolled_back_session_is_never_claimable(
    engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(engine)
    envelope = _pending()
    async with session_factory() as session:
        await SqlAlchemyOutboxAppender(session).append(envelope)
        await session.rollback()

    claimer = SqlAlchemyOutboxClaimer(session_factory)
    claimed = await claimer.claim(_NOTE_APPROVED, limit=10, worker_id="w1")

    assert claimed == []


async def test_envelope_committed_in_one_session_is_claimable_from_another(
    engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(engine)
    envelope = _pending()
    async with session_factory() as session:
        await SqlAlchemyOutboxAppender(session).append(envelope)
        await session.commit()

    claimer = SqlAlchemyOutboxClaimer(session_factory)
    claimed = await claimer.claim(_NOTE_APPROVED, limit=10, worker_id="w1")

    assert [claimed_envelope.id for claimed_envelope in claimed] == [envelope.id]
