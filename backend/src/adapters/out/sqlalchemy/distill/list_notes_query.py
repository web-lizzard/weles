from datetime import datetime
from typing import cast

from adapters.out.sqlalchemy.distill.models import DistillCardRow, DistillNoteRow
from application.distill.queries.list_notes import NoteListItemDTO
from domain.shared.identity.model import UserId
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlAlchemyListNotesQueryAdapter:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def list_notes(self, owner: UserId) -> list[NoteListItemDTO]:
        _ = owner
        async with self._session_factory() as session:
            last_updated_at = func.greatest(
                DistillNoteRow.updated_at,
                func.coalesce(
                    func.max(DistillCardRow.created_at), DistillNoteRow.updated_at
                ),
            ).label("last_updated_at")
            statement = (
                select(
                    DistillNoteRow.id,
                    DistillNoteRow.topic_label,
                    DistillNoteRow.distillation_status,
                    func.count(DistillCardRow.id).label("card_count"),
                    last_updated_at,
                )
                .outerjoin(
                    DistillCardRow,
                    (DistillCardRow.note_id == DistillNoteRow.id)
                    & (DistillCardRow.discard_reason.is_(None)),
                )
                .group_by(
                    DistillNoteRow.id,
                    DistillNoteRow.topic_label,
                    DistillNoteRow.distillation_status,
                    DistillNoteRow.updated_at,
                )
                .order_by(last_updated_at.desc())
            )
            result = await session.execute(statement)
            return [
                NoteListItemDTO(
                    note_id=note_id.value,
                    topic_label=topic_label,
                    distillation_status=distillation_status.value,
                    card_count=card_count,
                    last_updated_at=cast(datetime, last_updated_at_value),
                )
                for (
                    note_id,
                    topic_label,
                    distillation_status,
                    card_count,
                    last_updated_at_value,  # pyright: ignore[reportAny]
                ) in result.tuples()
            ]
