from uuid import UUID

from domain.distill.card import Card
from domain.distill.value_objects import NoteId


class InMemoryCardRepository:
    def __init__(self) -> None:
        self._cards: dict[UUID, Card] = {}

    async def save(self, _card: Card) -> None: ...

    async def list_by_note(self, _note_id: NoteId) -> list[Card]: ...

    def snapshot(self) -> dict[UUID, Card]: ...

    def restore(self, _snapshot: dict[UUID, Card]) -> None: ...
