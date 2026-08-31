from datetime import UTC, datetime

from pydantic import BaseModel

from domain.capture.exceptions import SessionTopicAlreadyAssignedError
from domain.capture.value_objects import SessionId, SessionStatus, SessionTopic


class CaptureSession(BaseModel):
    id: SessionId
    topic: SessionTopic | None
    status: SessionStatus
    created_at: datetime

    @classmethod
    def start(cls) -> "CaptureSession":
        return cls(
            id=SessionId.new(),
            topic=None,
            status=SessionStatus.OPEN,
            created_at=datetime.now(UTC),
        )

    def assign_topic(self, topic: SessionTopic) -> None:
        if self.topic is not None:
            raise SessionTopicAlreadyAssignedError
        self.topic = topic
