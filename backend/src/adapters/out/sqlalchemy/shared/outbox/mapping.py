# pyright: reportUnusedParameter=false
from adapters.out.sqlalchemy.shared.outbox.models import OutboxEnvelopeRow
from domain.shared.outbox.model import OutboxEnvelope


def to_row(envelope: OutboxEnvelope) -> OutboxEnvelopeRow:
    raise NotImplementedError


def to_envelope(row: OutboxEnvelopeRow) -> OutboxEnvelope:
    raise NotImplementedError
