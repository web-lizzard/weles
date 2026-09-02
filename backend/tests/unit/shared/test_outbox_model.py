from datetime import UTC, datetime

import pytest

from domain.shared.outbox.exceptions import EnvelopeNotPendingError
from domain.shared.outbox.model import (
    EnvelopeId,
    EnvelopeStatus,
    EnvelopeType,
    OutboxEnvelope,
)

_NOTE_APPROVED = EnvelopeType(name="note_approved")


def _envelope(status: EnvelopeStatus, attempts: int = 0) -> OutboxEnvelope:
    return OutboxEnvelope(
        id=EnvelopeId.new(),
        type=_NOTE_APPROVED,
        payload={"note_id": "abc"},
        status=status,
        attempts=attempts,
        created_at=datetime.now(UTC),
        claimed_at=None,
        claimed_by=None,
    )


def test_envelope_type_equality_matches_name_and_version() -> None:
    note_approved = EnvelopeType(name="note_approved")
    note_approved_v2 = EnvelopeType(name="note_approved", version=2)

    assert note_approved == EnvelopeType(name="note_approved")
    assert note_approved == EnvelopeType(name="note_approved", version=1)
    assert note_approved != note_approved_v2
    assert note_approved != EnvelopeType(name="other_event")


def test_pending_builds_envelope_with_zero_attempts_and_no_claim_fields() -> None:
    envelope = OutboxEnvelope.pending(_NOTE_APPROVED, {"note_id": "abc"})

    assert envelope.status == EnvelopeStatus.PENDING
    assert envelope.type == _NOTE_APPROVED
    assert envelope.payload == {"note_id": "abc"}
    assert envelope.attempts == 0
    assert envelope.claimed_at is None
    assert envelope.claimed_by is None
    assert envelope.created_at.tzinfo is UTC


def test_claim_then_consume_moves_pending_through_processing_to_consumed() -> None:
    envelope = _envelope(EnvelopeStatus.PENDING)

    envelope.claim("worker-1")
    assert envelope.status == EnvelopeStatus.PROCESSING
    assert envelope.claimed_by == "worker-1"
    assert envelope.claimed_at is not None
    assert envelope.attempts == 1

    envelope.consume()
    assert envelope.status == EnvelopeStatus.CONSUMED


def test_claim_raises_when_envelope_is_not_pending() -> None:
    envelope = _envelope(EnvelopeStatus.PROCESSING)

    with pytest.raises(EnvelopeNotPendingError):
        envelope.claim("worker-1")


@pytest.mark.parametrize(
    ("attempts", "max_attempts", "expected_status"),
    [
        pytest.param(1, 3, EnvelopeStatus.PENDING, id="below_limit_retries"),
        pytest.param(3, 3, EnvelopeStatus.FAILED, id="at_limit_dead_letters"),
    ],
)
def test_fail_retries_below_the_limit_and_dead_letters_at_it(
    attempts: int, max_attempts: int, expected_status: EnvelopeStatus
) -> None:
    envelope = _envelope(EnvelopeStatus.PROCESSING, attempts=attempts)
    envelope.claimed_at = datetime.now(UTC)
    envelope.claimed_by = "worker-1"

    envelope.fail(max_attempts)

    assert envelope.status == expected_status
    if expected_status == EnvelopeStatus.PENDING:
        assert envelope.claimed_at is None
        assert envelope.claimed_by is None
