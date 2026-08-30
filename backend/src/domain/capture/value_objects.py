from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel


class MessageRole(StrEnum):
    USER = "user"
    AGENT = "agent"


class SessionStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class Topic(BaseModel, frozen=True):
    value: str


class MessageContent(BaseModel, frozen=True):
    value: str


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
