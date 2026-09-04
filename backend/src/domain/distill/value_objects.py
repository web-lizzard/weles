from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator

from domain.distill.exceptions import (
    CardSideTooLongError,
    DistillEmptyNoteContentError,
    DistillNoteContentTooLongError,
    EmptyAnchorError,
    EmptyCardSideError,
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

    @field_validator("value", mode="before")
    @classmethod
    def _canonicalize_value(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def _validate_value(self) -> "CardSide":
        if not self.value:
            raise EmptyCardSideError
        if len(self.value) > CARD_SIDE_MAX_LENGTH:
            raise CardSideTooLongError
        return self


class Anchor(BaseModel, frozen=True):
    quote: str

    @field_validator("quote", mode="before")
    @classmethod
    def _canonicalize_quote(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def _validate_quote(self) -> "Anchor":
        if not self.quote:
            raise EmptyAnchorError
        if len(self.quote) > ANCHOR_MAX_LENGTH:
            raise CardSideTooLongError
        return self


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

    def breach(self, front: CardSide, back: CardSide) -> str | None:
        if len(front.value) > self.front_max:
            return f"front exceeds front_max={self.front_max}"
        if len(back.value) > self.back_max:
            return f"back exceeds back_max={self.back_max}"
        return None
