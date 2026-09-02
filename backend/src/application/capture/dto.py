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


class DraftTopicEvent(BaseModel):
    type: Literal["draft_topic"] = "draft_topic"
    label: str
    reused: bool


class DraftTagEvent(BaseModel):
    type: Literal["draft_tag"] = "draft_tag"
    label: str
    reused: bool


class DraftDeltaEvent(BaseModel):
    type: Literal["draft_delta"] = "draft_delta"
    text: str


class DraftDoneEvent(BaseModel):
    type: Literal["draft_done"] = "draft_done"
    note_id: UUID
    topic: str
    content: str
    tags: list[str]


ReplyStreamEvent = Annotated[
    ReplyDeltaEvent
    | ReplyDoneEvent
    | ReplyErrorEvent
    | DraftTopicEvent
    | DraftTagEvent
    | DraftDeltaEvent
    | DraftDoneEvent,
    Field(discriminator="type"),
]
