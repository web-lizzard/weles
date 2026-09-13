from adapters.out.sqlalchemy.capture.mapping import (
    capture_session_to_domain,
    capture_session_to_row,
)
from adapters.out.sqlalchemy.capture.models import CaptureSessionRow
from domain.capture.capture_session import CaptureSession
from domain.capture.value_objects import SessionId
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyCaptureSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def get(self, session_id: SessionId) -> CaptureSession | None:
        statement = select(CaptureSessionRow).where(CaptureSessionRow.id == session_id)
        row = (await self._session.execute(statement)).scalar_one_or_none()
        return capture_session_to_domain(row) if row is not None else None

    async def save(self, session: CaptureSession) -> None:
        statement = select(CaptureSessionRow).where(CaptureSessionRow.id == session.id)
        existing = (await self._session.execute(statement)).scalar_one_or_none()
        updated = capture_session_to_row(session)
        if existing is None:
            self._session.add(updated)
        else:
            existing.topic = updated.topic
            existing.note_id = updated.note_id
            existing.status = updated.status
            existing.phase = updated.phase
            existing.drafting_consent = updated.drafting_consent
            existing.conversation_request = updated.conversation_request
            existing.assessments = updated.assessments
            existing.version = existing.version + 1
        await self._session.flush()
