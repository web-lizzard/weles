from typing import Protocol

from domain.capture.capture_session import CaptureSession
from domain.capture.message import Message
from domain.capture.value_objects import SessionId


class CaptureSessionRepository(Protocol):
    async def get(self, session_id: SessionId) -> CaptureSession | None: ...

    async def save(self, session: CaptureSession) -> None: ...


class MessageRepository(Protocol):
    async def add(self, message: Message) -> None: ...
