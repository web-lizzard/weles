from adapters.out.sqlalchemy.distill.models import DistillNoteRow
from application.distill.queries.get_note import (
    NoteBlockDTO,
    NoteDetailDTO,
    NoteDetailTagDTO,
    NoteDetailTopicDTO,
)
from domain.distill.exceptions import DistillNoteNotFoundError
from domain.distill.note_document import NoteDocument
from domain.distill.value_objects import NoteId
from domain.shared.identity.model import UserId
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload


class SqlAlchemyGetNoteQueryAdapter:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def get_note(self, owner: UserId, note_id: NoteId) -> NoteDetailDTO:
        _ = owner
        async with self._session_factory() as session:
            statement = (
                select(DistillNoteRow)
                .where(DistillNoteRow.id == note_id)
                .options(selectinload(DistillNoteRow.tags))
            )
            row = (await session.execute(statement)).scalar_one_or_none()
            if row is None:
                raise DistillNoteNotFoundError
            document = NoteDocument.of(row.content)
            return NoteDetailDTO(
                note_id=row.id.value,
                topic=NoteDetailTopicDTO(id=row.topic_id, label=row.topic_label),
                content=row.content.value,
                blocks=[
                    NoteBlockDTO(index=block.index, text=block.text)
                    for block in document.blocks
                ],
                tags=[
                    NoteDetailTagDTO(id=tag.tag_id, label=tag.label) for tag in row.tags
                ],
                distillation_status=row.distillation_status.value,
                approved_at=row.approved_at,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
