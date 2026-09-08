from application.distill.queries.list_cards_for_note import CardListItemDTO
from domain.distill.ports import CardRepository, NoteRepository
from domain.distill.value_objects import NoteId


class InMemoryListCardsForNoteQueryAdapter:
    def __init__(
        self, note_repository: NoteRepository, card_repository: CardRepository
    ) -> None:
        self._note_repository: NoteRepository = note_repository
        self._card_repository: CardRepository = card_repository

    async def list_cards_for_note(self, note_id: NoteId) -> list[CardListItemDTO]:
        raise NotImplementedError(note_id)
