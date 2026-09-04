from typing import Protocol

from domain.distill.card import Card
from domain.distill.note import Note
from domain.distill.value_objects import NoteId


class NoteRepository(Protocol):
    async def save(self, note: Note) -> None: ...

    async def get(self, note_id: NoteId) -> Note | None: ...


class CardRepository(Protocol):
    async def save(self, card: Card) -> None: ...

    async def list_by_note(self, note_id: NoteId) -> list[Card]: ...
