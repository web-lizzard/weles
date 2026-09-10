from collections.abc import Sequence

from domain.distill.card import Card
from domain.distill.ports import CardRepository, NoteRepository
from domain.remember.ports import ReviewableCard
from domain.remember.value_objects import CardId


class InMemoryReviewCatalog:
    """The one place a distill card becomes a remember card.

    A discarded card is simply not offered, and distill's own CardId
    never leaves this adapter.
    """

    def __init__(
        self, note_repository: NoteRepository, card_repository: CardRepository
    ) -> None:
        self._notes: NoteRepository = note_repository
        self._cards: CardRepository = card_repository

    async def list_reviewable(self) -> Sequence[ReviewableCard]:
        return [_as_reviewable(card) for card in await self._live_cards()]

    async def get_reviewable(self, card_id: CardId) -> ReviewableCard | None:
        for card in await self._live_cards():
            if card.id.value == card_id.value:
                return _as_reviewable(card)
        return None

    async def _live_cards(self) -> list[Card]:
        live: list[Card] = []
        for note in await self._notes.list_all():
            live.extend(
                card
                for card in await self._cards.list_by_note(note.id)
                if card.discard is None
            )
        return live


def _as_reviewable(card: Card) -> ReviewableCard:
    return ReviewableCard(
        id=CardId(value=card.id.value),
        front=card.front.value,
        back=card.back.value,
    )
