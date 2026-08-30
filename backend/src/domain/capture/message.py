from datetime import datetime

from pydantic import BaseModel

from domain.capture.value_objects import (
    MessageContent,
    MessageId,
    MessageRole,
    SessionId,
)


class Message(BaseModel, frozen=True):
    id: MessageId
    session_id: SessionId
    role: MessageRole
    content: MessageContent
    created_at: datetime

    @classmethod
    def record(
        cls,
        session_id: SessionId,  # pyright: ignore[reportUnusedParameter]
        role: MessageRole,  # pyright: ignore[reportUnusedParameter]
        content: MessageContent,  # pyright: ignore[reportUnusedParameter]
    ) -> "Message":
        raise NotImplementedError
