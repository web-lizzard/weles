from domain.capture.capture_session import CaptureSession
from domain.capture.value_objects import SessionId
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyCaptureSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def get(self, session_id: SessionId) -> CaptureSession | None:
        _ = session_id
        raise NotImplementedError

    async def save(self, session: CaptureSession) -> None:
        _ = session
        raise NotImplementedError
