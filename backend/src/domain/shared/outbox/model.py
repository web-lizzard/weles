from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel


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


class OutboxEnvelope(BaseModel):
    id: EnvelopeId
    type: str
    payload: dict[str, object]
    status: EnvelopeStatus
    attempts: int
    created_at: datetime
    claimed_at: datetime | None
    claimed_by: str | None

    @classmethod
    def pending(cls, _type: str, _payload: dict[str, object]) -> "OutboxEnvelope":
        raise NotImplementedError

    def claim(self, _worker_id: str) -> None:
        raise NotImplementedError

    def consume(self) -> None:
        raise NotImplementedError

    def fail(self, _max_attempts: int) -> None:
        raise NotImplementedError
