from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, field_validator, model_validator

from domain.capture.exceptions import (
    EmptyEmbeddingError,
    EmptyLabelError,
    EmptyMessageContentError,
    EmptyNoteContentError,
    EmptySessionTopicError,
    LabelTooLongError,
    MessageContentTooLongError,
    NoteContentTooLongError,
    SessionTopicTooLongError,
)

SESSION_TOPIC_MAX_LENGTH = 200
MESSAGE_CONTENT_MAX_LENGTH = 4000
LABEL_MAX_LENGTH = 120
NOTE_CONTENT_MAX_LENGTH = 20000


class MessageRole(StrEnum):
    USER = "user"
    AGENT = "agent"


class SessionStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class NoteStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    DISCARDED = "discarded"


class SessionTopic(BaseModel, frozen=True):
    value: str

    @field_validator("value", mode="before")
    @classmethod
    def _canonicalize_value(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def _validate_value(self) -> "SessionTopic":
        if not self.value:
            raise EmptySessionTopicError
        if len(self.value) > SESSION_TOPIC_MAX_LENGTH:
            raise SessionTopicTooLongError
        return self


class MessageContent(BaseModel, frozen=True):
    value: str

    @field_validator("value", mode="before")
    @classmethod
    def _canonicalize_value(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def _validate_value(self) -> "MessageContent":
        if not self.value:
            raise EmptyMessageContentError
        if len(self.value) > MESSAGE_CONTENT_MAX_LENGTH:
            raise MessageContentTooLongError
        return self


class SessionId(BaseModel, frozen=True):
    value: UUID

    @classmethod
    def new(cls) -> "SessionId":
        return cls(value=uuid4())


class MessageId(BaseModel, frozen=True):
    value: UUID

    @classmethod
    def new(cls) -> "MessageId":
        return cls(value=uuid4())


class Label(BaseModel, frozen=True):
    value: str

    @field_validator("value", mode="before")
    @classmethod
    def _canonicalize_value(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def _validate_value(self) -> "Label":
        if not self.value:
            raise EmptyLabelError
        if len(self.value) > LABEL_MAX_LENGTH:
            raise LabelTooLongError
        return self


class Embedding(BaseModel, frozen=True):
    values: tuple[float, ...]

    @model_validator(mode="after")
    def _validate_values(self) -> "Embedding":
        if not self.values:
            raise EmptyEmbeddingError
        return self


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
            raise EmptyNoteContentError
        if len(self.value) > NOTE_CONTENT_MAX_LENGTH:
            raise NoteContentTooLongError
        return self


class NoteId(BaseModel, frozen=True):
    value: UUID

    @classmethod
    def new(cls) -> "NoteId":
        return cls(value=uuid4())


class TopicId(BaseModel, frozen=True):
    value: UUID

    @classmethod
    def new(cls) -> "TopicId":
        return cls(value=uuid4())


class TagId(BaseModel, frozen=True):
    value: UUID

    @classmethod
    def new(cls) -> "TagId":
        return cls(value=uuid4())
