from adapters.out.sqlalchemy.shared.outbox.models import OutboxEnvelopeRow
from domain.shared.outbox.model import (
    EnvelopeId,
    EnvelopeStatus,
    EnvelopeType,
    OutboxEnvelope,
)


def to_row(envelope: OutboxEnvelope) -> OutboxEnvelopeRow:
    return OutboxEnvelopeRow(
        id=envelope.id.value,
        type_name=envelope.type.name,
        type_version=envelope.type.version,
        payload=envelope.payload,
        status=envelope.status.value,
        attempts=envelope.attempts,
        created_at=envelope.created_at,
        claimed_at=envelope.claimed_at,
        claimed_by=envelope.claimed_by,
    )


def to_envelope(row: OutboxEnvelopeRow) -> OutboxEnvelope:
    return OutboxEnvelope(
        id=EnvelopeId(value=row.id),
        type=EnvelopeType(name=row.type_name, version=row.type_version),
        payload=row.payload,
        status=EnvelopeStatus(row.status),
        attempts=row.attempts,
        created_at=row.created_at,
        claimed_at=row.claimed_at,
        claimed_by=row.claimed_by,
    )
