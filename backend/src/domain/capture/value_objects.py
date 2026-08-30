from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, field_validator, model_validator

from domain.capture.exceptions import (
    EmptyMessageContentError,
    EmptyTopicError,
    MessageContentTooLongError,
    TopicTooLongError,
)

TOPIC_MAX_LENGTH = 200
MESSAGE_CONTENT_MAX_LENGTH = 4000


class MessageRole(StrEnum):
    USER = "user"
    AGENT = "agent"


class SessionStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class Topic(BaseModel, frozen=True):
    value: str

    @field_validator("value", mode="before")
    @classmethod
    def _canonicalize_value(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def _validate_value(self) -> "Topic":
        if not self.value:
            raise EmptyTopicError
        if len(self.value) > TOPIC_MAX_LENGTH:
            raise TopicTooLongError
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
