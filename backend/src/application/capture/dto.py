from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class StartCaptureSessionResponseDTO(BaseModel):
    session_id: UUID


class SendMessageRequestDTO(BaseModel):
    content: str


class ReplyDeltaEvent(BaseModel):
    type: Literal["delta"] = "delta"
    text: str


class ReplyDoneEvent(BaseModel):
    type: Literal["done"] = "done"
    message_id: UUID
    content: str
    topic: str
    coverage_confidence: float = Field(
        ge=0.0,
        le=1.0,
    )


class ReplyErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    code: str
    detail: str


ReplyStreamEvent = Annotated[
    ReplyDeltaEvent | ReplyDoneEvent | ReplyErrorEvent, Field(discriminator="type")
]
