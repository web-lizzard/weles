# pyright: reportUnusedParameter=false

from domain.distill.note import Note
from domain.distill.value_objects import NoteId
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyNoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def save(self, note: Note) -> None:
        raise NotImplementedError

    async def get(self, note_id: NoteId) -> Note | None:
        raise NotImplementedError

    async def list_all(self) -> list[Note]:
        raise NotImplementedError
