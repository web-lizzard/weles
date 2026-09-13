from datetime import datetime
from uuid import UUID

from adapters.out.sqlalchemy.base import Base
from domain.shared.outbox.model import EnvelopeStatus
from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

_STATUS_VALUES = tuple(status.value for status in EnvelopeStatus)


class OutboxEnvelopeRow(Base):
    __tablename__: str = "outbox_envelopes"
    __table_args__: tuple[CheckConstraint, Index] = (
        CheckConstraint(
            f"status IN {_STATUS_VALUES}",
            name="status_valid",
        ),
        Index(
            "ix_outbox_envelopes_pending_claim_order",
            "type_name",
            "type_version",
            "created_at",
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    type_name: Mapped[str] = mapped_column(String, nullable=False)
    type_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    claimed_by: Mapped[str | None] = mapped_column(String, nullable=True)
