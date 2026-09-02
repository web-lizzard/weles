from application.capture.dto import ApproveNoteResponseDTO
from application.capture.ports import UnitOfWork
from domain.capture.value_objects import SessionId


class ApproveNoteCommand:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow: UnitOfWork = uow

    async def handle(self, _session_id: SessionId) -> ApproveNoteResponseDTO:
        raise NotImplementedError
