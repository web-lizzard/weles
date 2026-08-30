from datetime import datetime

from pydantic import BaseModel

from domain.capture.value_objects import SessionId, SessionStatus, Topic


class CaptureSession(BaseModel):
    id: SessionId
    topic: Topic | None
    status: SessionStatus
    created_at: datetime

    @classmethod
    def start(cls) -> "CaptureSession":
        raise NotImplementedError

    def assign_topic(self, topic: Topic) -> None:  # pyright: ignore[reportUnusedParameter]
        raise NotImplementedError
