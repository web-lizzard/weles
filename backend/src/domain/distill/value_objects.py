from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator

from domain.distill.exceptions import (
    DistillEmptyNoteContentError,
    DistillNoteContentTooLongError,
)

NOTE_CONTENT_MAX_LENGTH = 20000
CARD_SIDE_MAX_LENGTH = 2000
ANCHOR_MAX_LENGTH = 4000


class NoteId(BaseModel, frozen=True):
    value: UUID


class SessionId(BaseModel, frozen=True):
    value: UUID


class TopicSnapshot(BaseModel, frozen=True):
    id: UUID
    label: str


class TagSnapshot(BaseModel, frozen=True):
    id: UUID
    label: str


class NoteContent(BaseModel, frozen=True):
    value: str

    @field_validator("value", mode="before")
    @classmethod
    def _canonicalize_value(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def _validate_value(self) -> "NoteContent":
        if not self.value:
            raise DistillEmptyNoteContentError
        if len(self.value) > NOTE_CONTENT_MAX_LENGTH:
            raise DistillNoteContentTooLongError
        return self


class DistillationStatus(StrEnum):
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class CardId(BaseModel, frozen=True):
    value: UUID


class CardSide(BaseModel, frozen=True):
    value: str


class Anchor(BaseModel, frozen=True):
    quote: str


class DiscardReason(StrEnum):
    UNGROUNDED = "ungrounded"
    OVERSIZED = "oversized"
    USER_AUDIT = "user_audit"


class AnchorResolution(StrEnum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


class Discard(BaseModel, frozen=True):
    reason: DiscardReason
    detail: str | None
    discarded_at: datetime


class CardLengthPolicy(BaseModel, frozen=True):
    front_max: int
    back_max: int

    def breach(self, _front: CardSide, _back: CardSide) -> str | None: ...
