from domain.capture.capture_session import CaptureSession
from domain.capture.value_objects import SessionId


class InMemoryCaptureSessionRepository:
    async def get(
        self,
        session_id: SessionId,  # pyright: ignore[reportUnusedParameter]
    ) -> CaptureSession | None:
        raise NotImplementedError

    async def save(
        self,
        session: CaptureSession,  # pyright: ignore[reportUnusedParameter]
    ) -> None:
        raise NotImplementedError
