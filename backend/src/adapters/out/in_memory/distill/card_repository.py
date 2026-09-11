import copy
from uuid import UUID

from domain.distill.card import Card
from domain.distill.value_objects import CardId, NoteId


class InMemoryCardRepository:
    def __init__(self) -> None:
        self._cards: dict[UUID, Card] = {}

    async def save(self, card: Card) -> None:
        self._cards[card.id.value] = card

    async def get(self, card_id: CardId) -> Card | None:
        return self._cards.get(card_id.value)

    async def list_by_note(self, note_id: NoteId) -> list[Card]:
        return [card for card in self._cards.values() if card.note_id == note_id]

    def snapshot(self) -> dict[UUID, Card]:
        return copy.deepcopy(self._cards)

    def restore(self, snapshot: dict[UUID, Card]) -> None:
        self._cards = copy.deepcopy(snapshot)
