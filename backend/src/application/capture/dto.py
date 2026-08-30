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


ReplyStreamEvent = Annotated[
    ReplyDeltaEvent | ReplyDoneEvent, Field(discriminator="type")
]
