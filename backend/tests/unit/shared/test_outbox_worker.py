import asyncio

import pytest

from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.claimer import InMemoryOutboxClaimer
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from adapters.out.worker.outbox_worker import OutboxWorker
from domain.shared.outbox.model import (
    EnvelopeId,
    EnvelopeStatus,
    EnvelopeType,
    OutboxEnvelope,
)

_NOTE_APPROVED = EnvelopeType(name="note_approved")
_OTHER_EVENT = EnvelopeType(name="other_event")


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


class _RaisingThenCancellingClaimer:
    def __init__(self) -> None:
        self.calls: int = 0

    async def claim(
        self, envelope_type: EnvelopeType, limit: int, worker_id: str
    ) -> list[OutboxEnvelope]:
        del envelope_type, limit, worker_id
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("transient claim failure")
        raise asyncio.CancelledError

    async def ack(self, envelope: OutboxEnvelope) -> None:
        del envelope

    async def fail(self, envelope: OutboxEnvelope) -> None:
        del envelope


async def test_run_once_retries_a_handler_that_fails_once_then_succeeds() -> None:
    store = InMemoryOutboxStore()
    appender = InMemoryOutboxAppender(store)
    claimer = InMemoryOutboxClaimer(store)
    envelope = OutboxEnvelope.pending(_NOTE_APPROVED, {"n": 1})
    await appender.append(envelope)
    handler = _FlakyHandler(_NOTE_APPROVED, fail_times=1)
    worker = OutboxWorker(
        claimer, [handler], worker_id="w1", batch_size=10, max_attempts=3
    )

    first_acked = await worker.run_once()
    assert first_acked == 0
    stored_after_first = store.all()[0]
    assert stored_after_first.status == EnvelopeStatus.PENDING
    assert stored_after_first.attempts == 1

    second_acked = await worker.run_once()
    assert second_acked == 1
    assert store.all()[0].status == EnvelopeStatus.CONSUMED
    assert handler.handled == [envelope.id]


async def test_run_once_dead_letters_envelope_after_max_attempts_failures() -> None:
    store = InMemoryOutboxStore()
    appender = InMemoryOutboxAppender(store)
    claimer = InMemoryOutboxClaimer(store)
    envelope = OutboxEnvelope.pending(_NOTE_APPROVED, {"n": 1})
    await appender.append(envelope)
    handler = _FlakyHandler(_NOTE_APPROVED, fail_times=10)
    worker = OutboxWorker(
        claimer, [handler], worker_id="w1", batch_size=10, max_attempts=3
    )

    for _ in range(3):
        acked = await worker.run_once()
        assert acked == 0

    stored = store.all()[0]
    assert stored.status == EnvelopeStatus.FAILED
    assert stored.attempts == 3


async def test_run_once_leaves_envelope_pending_when_no_handler_claims_its_type() -> (
    None
):
    store = InMemoryOutboxStore()
    appender = InMemoryOutboxAppender(store)
    claimer = InMemoryOutboxClaimer(store)
    envelope = OutboxEnvelope.pending(_OTHER_EVENT, {"n": 1})
    await appender.append(envelope)
    handler = _FlakyHandler(_NOTE_APPROVED, fail_times=0)
    worker = OutboxWorker(
        claimer, [handler], worker_id="w1", batch_size=10, max_attempts=3
    )

    acked = await worker.run_once()

    assert acked == 0
    assert store.all()[0].status == EnvelopeStatus.PENDING
    assert handler.handled == []


async def test_two_workers_gather_processes_each_envelope_exactly_once() -> None:
    store = InMemoryOutboxStore()
    appender = InMemoryOutboxAppender(store)
    claimer = InMemoryOutboxClaimer(store)
    envelopes = [OutboxEnvelope.pending(_NOTE_APPROVED, {"n": i}) for i in range(6)]
    for envelope in envelopes:
        await appender.append(envelope)
    handler = _FlakyHandler(_NOTE_APPROVED, fail_times=0)
    worker_a = OutboxWorker(
        claimer, [handler], worker_id="w1", batch_size=10, max_attempts=3
    )
    worker_b = OutboxWorker(
        claimer, [handler], worker_id="w2", batch_size=10, max_attempts=3
    )

    acked_a, acked_b = await asyncio.gather(worker_a.run_once(), worker_b.run_once())

    assert acked_a + acked_b == 6
    assert sorted(handler.handled, key=str) == sorted(
        (envelope.id for envelope in envelopes), key=str
    )
    consumed = [e for e in store.all() if e.status == EnvelopeStatus.CONSUMED]
    assert len(consumed) == 6


async def test_run_forever_swallows_error_but_lets_cancelled_error_propagate() -> None:
    claimer = _RaisingThenCancellingClaimer()
    handler = _FlakyHandler(_NOTE_APPROVED, fail_times=0)
    worker = OutboxWorker(
        claimer, [handler], worker_id="w1", batch_size=10, max_attempts=3
    )

    with pytest.raises(asyncio.CancelledError):
        await worker.run_forever(0)

    assert claimer.calls == 2
