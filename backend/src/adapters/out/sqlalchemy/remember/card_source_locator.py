from adapters.out.sqlalchemy.distill.models import DistillCardRow, DistillNoteRow
from domain.distill.note_document import NoteDocument
from domain.distill.value_objects import CardId as DistillCardId
from domain.distill.value_objects import NoteContent
from domain.remember.ports import CardSource, SourceBlock, SourceSpan
from domain.remember.value_objects import CardId
from domain.shared.identity.model import UserId
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlAlchemyCardSourceLocator:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def locate(self, owner: UserId, card_id: CardId) -> CardSource | None:
        async with self._session_factory() as session:
            matched = (
                (
                    await session.execute(
                        select(DistillCardRow, DistillNoteRow.content)
                        .join(
                            DistillNoteRow, DistillCardRow.note_id == DistillNoteRow.id
                        )
                        .where(
                            DistillCardRow.id == DistillCardId(value=card_id.value),
                            DistillCardRow.discard_reason.is_(None),
                            DistillCardRow.owner_id == owner.value,
                        )
                    )
                )
                .tuples()
                .one_or_none()
            )
            if matched is None:
                return None
            card_row: DistillCardRow
            note_content: NoteContent
            card_row, note_content = matched
            document = NoteDocument.of(note_content)
            location = document.locate(card_row.anchor_quote)
            if location is None:
                return None
            return CardSource(
                blocks=[
                    SourceBlock(index=block.index, text=block.text)
                    for block in document.blocks
                ],
                span=SourceSpan(
                    block_index=location.block_index,
                    start=location.start,
                    end=location.end,
                ),
            )
