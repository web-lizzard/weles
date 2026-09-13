from application.distill.queries.list_cards_for_note import CardListItemDTO
from domain.distill.value_objects import NoteId
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlAlchemyListCardsForNoteQueryAdapter:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def list_cards_for_note(self, _note_id: NoteId) -> list[CardListItemDTO]:
        raise NotImplementedError
