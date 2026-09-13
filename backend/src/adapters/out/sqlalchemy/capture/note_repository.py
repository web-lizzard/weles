from domain.capture.note import Note
from domain.capture.value_objects import NoteId
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyNoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def add(self, note: Note) -> None:
        _ = note
        raise NotImplementedError

    async def get(self, note_id: NoteId) -> Note | None:
        _ = note_id
        raise NotImplementedError
