from datetime import UTC, datetime
from enum import StrEnum
from typing import override
from uuid import UUID, uuid4

from pydantic import BaseModel

from domain.shared.outbox.exceptions import (
    EnvelopeNotPendingError,
    EnvelopeNotProcessingError,
)


class EnvelopeStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    CONSUMED = "consumed"
    FAILED = "failed"


class EnvelopeId(BaseModel, frozen=True):
    value: UUID

    @classmethod
    def new(cls) -> "EnvelopeId":
        return cls(value=uuid4())


class EnvelopeType(BaseModel, frozen=True):
    name: str
    version: int = 1

    @override
    def __str__(self) -> str:
        return f"{self.name}@{self.version}"


class OutboxEnvelope(BaseModel):
    id: EnvelopeId
    type: EnvelopeType
    payload: dict[str, object]
    status: EnvelopeStatus
    attempts: int
    created_at: datetime
    claimed_at: datetime | None
    claimed_by: str | None

    @classmethod
    def pending(
        cls, type: EnvelopeType, payload: dict[str, object]
    ) -> "OutboxEnvelope":
        return cls(
            id=EnvelopeId.new(),
            type=type,
            payload=payload,
            status=EnvelopeStatus.PENDING,
            attempts=0,
            created_at=datetime.now(UTC),
            claimed_at=None,
            claimed_by=None,
        )

    def claim(self, worker_id: str) -> None:
        if self.status != EnvelopeStatus.PENDING:
            raise EnvelopeNotPendingError
        self.status = EnvelopeStatus.PROCESSING
        self.claimed_by = worker_id
        self.claimed_at = datetime.now(UTC)
        self.attempts += 1

    def consume(self) -> None:
        if self.status != EnvelopeStatus.PROCESSING:
            raise EnvelopeNotProcessingError
        self.status = EnvelopeStatus.CONSUMED

    def fail(self, max_attempts: int) -> None:
        if self.status != EnvelopeStatus.PROCESSING:
            raise EnvelopeNotProcessingError
        if self.attempts < max_attempts:
            self.status = EnvelopeStatus.PENDING
            self.claimed_at = None
            self.claimed_by = None
        else:
            self.status = EnvelopeStatus.FAILED
