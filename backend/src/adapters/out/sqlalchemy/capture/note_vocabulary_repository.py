from domain.capture.note import Note
from domain.capture.note_vocabulary import NoteVocabulary
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyNoteVocabularyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def resolve(self, note: Note) -> NoteVocabulary:
        _ = note
        raise NotImplementedError
