from datetime import UTC, datetime

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
        session_id: SessionId,
        role: MessageRole,
        content: MessageContent,
    ) -> "Message":
        return cls(
            id=MessageId.new(),
            session_id=session_id,
            role=role,
            content=content,
            created_at=datetime.now(UTC),
        )
