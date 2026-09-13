# pyright: reportUnusedParameter=false

from domain.distill.card import Card
from domain.distill.value_objects import CardId, NoteId
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyCardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def save(self, card: Card) -> None:
        raise NotImplementedError

    async def get(self, card_id: CardId) -> Card | None:
        raise NotImplementedError

    async def list_by_note(self, note_id: NoteId) -> list[Card]:
        raise NotImplementedError
