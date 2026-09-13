from application.distill.queries.get_note import NoteDetailDTO
from domain.distill.value_objects import NoteId
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlAlchemyGetNoteQueryAdapter:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def get_note(self, _note_id: NoteId) -> NoteDetailDTO:
        raise NotImplementedError
