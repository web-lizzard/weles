import copy
from uuid import UUID

from domain.capture.capture_session import CaptureSession
from domain.capture.value_objects import SessionId


class InMemoryCaptureSessionRepository:
    def __init__(self) -> None:
        self._sessions: dict[UUID, CaptureSession] = {}

    async def get(self, session_id: SessionId) -> CaptureSession | None:
        return self._sessions.get(session_id.value)

    async def save(self, session: CaptureSession) -> None:
        self._sessions[session.id.value] = session

    def snapshot(self) -> dict[UUID, CaptureSession]:
        return copy.deepcopy(self._sessions)

    def restore(self, snapshot: dict[UUID, CaptureSession]) -> None:
        self._sessions = copy.deepcopy(snapshot)
