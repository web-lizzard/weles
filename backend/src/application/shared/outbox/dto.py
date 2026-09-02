from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class OutboxEnvelopeDTO(BaseModel):
    id: UUID
    type: str
    status: str
    attempts: int
    created_at: datetime
    claimed_at: datetime | None
    claimed_by: str | None
