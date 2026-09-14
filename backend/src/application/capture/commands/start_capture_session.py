from application.capture.dto import StartCaptureSessionResponseDTO
from application.capture.ports import UnitOfWork
from domain.capture.capture_session import CaptureSession
from domain.shared.identity.model import UserId


class StartCaptureSessionCommand:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow: UnitOfWork = uow

    async def handle(self, owner: UserId) -> StartCaptureSessionResponseDTO:
        async with self._uow as uow:
            session = CaptureSession.start(owner)
            await uow.capture_sessions.save(session)
            await uow.commit()
        return StartCaptureSessionResponseDTO(session_id=session.id.value)
