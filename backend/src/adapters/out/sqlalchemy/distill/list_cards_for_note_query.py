from adapters.out.sqlalchemy.distill.models import DistillCardRow, DistillNoteRow
from application.distill.queries.list_cards_for_note import (
    AnchorLocationDTO,
    CardListItemDTO,
)
from domain.distill.exceptions import DistillNoteNotFoundError
from domain.distill.note_document import AnchorLocation, NoteDocument
from domain.distill.value_objects import NoteId
from domain.shared.identity.model import UserId
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlAlchemyListCardsForNoteQueryAdapter:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def list_cards_for_note(
        self, owner: UserId, note_id: NoteId
    ) -> list[CardListItemDTO]:
        async with self._session_factory() as session:
            note_row = (
                await session.execute(
                    select(DistillNoteRow).where(
                        DistillNoteRow.id == note_id,
                        DistillNoteRow.owner_id == owner.value,
                    )
                )
            ).scalar_one_or_none()
            if note_row is None:
                raise DistillNoteNotFoundError
            card_rows = (
                (
                    await session.execute(
                        select(DistillCardRow)
                        .where(
                            DistillCardRow.note_id == note_id,
                            DistillCardRow.discard_reason.is_(None),
                        )
                        .order_by(DistillCardRow.created_at, DistillCardRow.id)
                    )
                )
                .scalars()
                .all()
            )
            document = NoteDocument.of(note_row.content)
            return [
                CardListItemDTO(
                    card_id=card.id.value,
                    front=card.front.value,
                    back=card.back.value,
                    anchor_quote=card.anchor_quote.quote,
                    anchor_location=_to_anchor_location_dto(
                        document.locate(card.anchor_quote)
                    ),
                    created_at=card.created_at,
                )
                for card in card_rows
            ]


def _to_anchor_location_dto(
    location: AnchorLocation | None,
) -> AnchorLocationDTO | None:
    if location is None:
        return None
    return AnchorLocationDTO(
        block_index=location.block_index,
        start=location.start,
        end=location.end,
        precision=location.precision.value,
    )
