from adapters.out.sqlalchemy.capture.mapping import (
    capture_session_to_domain,
    capture_session_to_row,
)
from adapters.out.sqlalchemy.capture.models import CaptureSessionRow
from application.capture.exceptions import CaptureSessionConflictError
from domain.capture.capture_session import CaptureSession
from domain.capture.value_objects import SessionId
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyCaptureSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session
        self._versions: dict[SessionId, int] = {}

    async def get(self, session_id: SessionId) -> CaptureSession | None:
        statement = select(CaptureSessionRow).where(CaptureSessionRow.id == session_id)
        row = (await self._session.execute(statement)).scalar_one_or_none()
        if row is None:
            return None
        self._versions[session_id] = row.version
        return capture_session_to_domain(row)

    async def save(self, session: CaptureSession) -> None:
        expected = self._versions.get(session.id)
        if expected is None:
            statement = select(CaptureSessionRow).where(
                CaptureSessionRow.id == session.id
            )
            existing = (await self._session.execute(statement)).scalar_one_or_none()
            if existing is None:
                self._session.add(capture_session_to_row(session))
                await self._session.flush()
                self._versions[session.id] = 1
                return
            expected = existing.version
        mapped = capture_session_to_row(session)
        result = await self._session.execute(
            update(CaptureSessionRow)
            .where(
                CaptureSessionRow.id == session.id,
                CaptureSessionRow.version == expected,
            )
            .values(
                topic=mapped.topic,
                note_id=mapped.note_id,
                status=mapped.status,
                phase=mapped.phase,
                drafting_consent=mapped.drafting_consent,
                conversation_request=mapped.conversation_request,
                assessments=mapped.assessments,
                version=expected + 1,
            )
            .returning(CaptureSessionRow.id)
            .execution_options(synchronize_session=False)
        )
        if result.scalar_one_or_none() is None:
            raise CaptureSessionConflictError
        self._versions[session.id] = expected + 1
        self._expire_row(session.id)
        await self._session.flush()

    def _expire_row(self, session_id: SessionId) -> None:
        for instance in self._session.identity_map.values():
            if isinstance(instance, CaptureSessionRow) and instance.id == session_id:
                self._session.expire(instance)
                return
