from application.distill.queries.list_cards_for_note import CardListItemDTO
from domain.distill.exceptions import DistillNoteNotFoundError
from domain.distill.ports import CardRepository, NoteRepository
from domain.distill.value_objects import NoteId


class InMemoryListCardsForNoteQueryAdapter:
    def __init__(
        self, note_repository: NoteRepository, card_repository: CardRepository
    ) -> None:
        self._note_repository: NoteRepository = note_repository
        self._card_repository: CardRepository = card_repository

    async def list_cards_for_note(self, note_id: NoteId) -> list[CardListItemDTO]:
        note = await self._note_repository.get(note_id)
        if note is None:
            raise DistillNoteNotFoundError
        live_cards = [
            card
            for card in await self._card_repository.list_by_note(note_id)
            if card.discard is None
        ]
        live_cards.sort(key=lambda card: card.created_at)
        return [
            CardListItemDTO(
                card_id=card.id.value,
                front=card.front.value,
                back=card.back.value,
                anchor_quote=card.anchor.quote,
                created_at=card.created_at,
            )
            for card in live_cards
        ]
