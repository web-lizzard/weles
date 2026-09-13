from adapters.out.sqlalchemy.distill.mapping import card_to_domain, card_to_row
from adapters.out.sqlalchemy.distill.models import DistillCardRow
from domain.distill.card import Card
from domain.distill.value_objects import CardId, NoteId
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyCardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def save(self, card: Card) -> None:
        statement = select(DistillCardRow).where(DistillCardRow.id == card.id)
        existing = (await self._session.execute(statement)).scalar_one_or_none()
        if existing is None:
            self._session.add(card_to_row(card))
        else:
            existing.note_id = card.note_id
            existing.front = card.front
            existing.back = card.back
            existing.anchor_quote = card.anchor
            discard = card.discard
            existing.discard_reason = discard.reason if discard is not None else None
            existing.discard_detail = discard.detail if discard is not None else None
            existing.discarded_at = (
                discard.discarded_at if discard is not None else None
            )
            existing.created_at = card.created_at
        await self._session.flush()

    async def get(self, card_id: CardId) -> Card | None:
        statement = select(DistillCardRow).where(DistillCardRow.id == card_id)
        row = (await self._session.execute(statement)).scalar_one_or_none()
        return card_to_domain(row) if row is not None else None

    async def list_by_note(self, note_id: NoteId) -> list[Card]:
        statement = (
            select(DistillCardRow)
            .where(DistillCardRow.note_id == note_id)
            .order_by(DistillCardRow.created_at, DistillCardRow.id)
        )
        rows = (await self._session.execute(statement)).scalars().all()
        return [card_to_domain(row) for row in rows]
