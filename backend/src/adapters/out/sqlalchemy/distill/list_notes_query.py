from application.distill.queries.list_notes import NoteListItemDTO
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlAlchemyListNotesQueryAdapter:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def list_notes(self) -> list[NoteListItemDTO]:
        raise NotImplementedError
