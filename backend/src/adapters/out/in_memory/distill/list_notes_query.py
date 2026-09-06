from application.distill.queries.list_notes import NoteListItemDTO
from domain.distill.ports import CardRepository, NoteRepository


class InMemoryListNotesQuery:
    def __init__(
        self, note_repository: NoteRepository, card_repository: CardRepository
    ) -> None:
        self._note_repository: NoteRepository = note_repository
        self._card_repository: CardRepository = card_repository

    async def list_notes(self) -> list[NoteListItemDTO]:
        raise NotImplementedError
