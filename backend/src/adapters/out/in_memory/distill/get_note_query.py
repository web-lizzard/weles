from application.distill.queries.get_note import NoteDetailDTO
from domain.distill.ports import NoteRepository
from domain.distill.value_objects import NoteId


class InMemoryGetNoteQueryAdapter:
    def __init__(self, note_repository: NoteRepository) -> None:
        self._note_repository: NoteRepository = note_repository

    async def get_note(self, note_id: NoteId) -> NoteDetailDTO:
        raise NotImplementedError(note_id)
