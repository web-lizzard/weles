from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, model_validator

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

    @model_validator(mode="after")
    def _validate_value(self) -> "Topic":
        stripped = self.value.strip()
        if not stripped:
            raise EmptyTopicError
        if len(stripped) > TOPIC_MAX_LENGTH:
            raise TopicTooLongError
        return self


class MessageContent(BaseModel, frozen=True):
    value: str

    @model_validator(mode="after")
    def _validate_value(self) -> "MessageContent":
        stripped = self.value.strip()
        if not stripped:
            raise EmptyMessageContentError
        if len(stripped) > MESSAGE_CONTENT_MAX_LENGTH:
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
