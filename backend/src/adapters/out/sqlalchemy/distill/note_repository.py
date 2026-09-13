from adapters.out.sqlalchemy.distill.mapping import note_to_domain, note_to_row
from adapters.out.sqlalchemy.distill.models import DistillNoteRow, DistillNoteTagRow
from domain.distill.note import Note
from domain.distill.value_objects import NoteId
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class SqlAlchemyNoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def save(self, note: Note) -> None:
        statement = (
            select(DistillNoteRow)
            .where(DistillNoteRow.id == note.id)
            .options(selectinload(DistillNoteRow.tags))
        )
        existing = (await self._session.execute(statement)).scalar_one_or_none()
        if existing is None:
            self._session.add(note_to_row(note))
        else:
            existing.session_id = note.session_id
            existing.topic_id = note.topic.id
            existing.topic_label = note.topic.label
            existing.content = note.content
            existing.distillation_status = note.distillation_status
            existing.approved_at = note.approved_at
            existing.created_at = note.created_at
            existing.updated_at = note.updated_at
            existing.tags = [
                DistillNoteTagRow(
                    note_id=note.id,
                    position=position,
                    tag_id=tag.id,
                    label=tag.label,
                )
                for position, tag in enumerate(note.tags)
            ]
        await self._session.flush()

    async def get(self, note_id: NoteId) -> Note | None:
        statement = (
            select(DistillNoteRow)
            .where(DistillNoteRow.id == note_id)
            .options(selectinload(DistillNoteRow.tags))
        )
        row = (await self._session.execute(statement)).scalar_one_or_none()
        return note_to_domain(row) if row is not None else None

    async def list_all(self) -> list[Note]:
        statement = (
            select(DistillNoteRow)
            .options(selectinload(DistillNoteRow.tags))
            .order_by(DistillNoteRow.created_at, DistillNoteRow.id)
        )
        rows = (await self._session.execute(statement)).scalars().all()
        return [note_to_domain(row) for row in rows]
