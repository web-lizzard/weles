from adapters.out.sqlalchemy.capture.mapping import note_to_domain, note_to_row
from adapters.out.sqlalchemy.capture.models import CaptureNoteRow, CaptureNoteTagRow
from domain.capture.note import Note
from domain.capture.value_objects import NoteId
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class SqlAlchemyNoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def add(self, note: Note) -> None:
        statement = (
            select(CaptureNoteRow)
            .where(CaptureNoteRow.id == note.id)
            .options(selectinload(CaptureNoteRow.tags))
        )
        existing = (await self._session.execute(statement)).scalar_one_or_none()
        if existing is None:
            self._session.add(note_to_row(note))
        else:
            existing.session_id = note.session_id
            existing.topic_id = note.topic_id
            existing.content = note.content
            existing.status = note.status
            existing.created_at = note.created_at
            existing.approved_at = note.approved_at
            existing.tags = [
                CaptureNoteTagRow(note_id=note.id, position=position, tag_id=tag_id)
                for position, tag_id in enumerate(note.tag_ids)
            ]
        await self._session.flush()

    async def get(self, note_id: NoteId) -> Note | None:
        statement = (
            select(CaptureNoteRow)
            .where(CaptureNoteRow.id == note_id)
            .options(selectinload(CaptureNoteRow.tags))
        )
        row = (await self._session.execute(statement)).scalar_one_or_none()
        return note_to_domain(row) if row is not None else None
