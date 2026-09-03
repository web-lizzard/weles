from typing import Protocol

from domain.distill.note import Note
from domain.distill.value_objects import NoteId


class NoteRepository(Protocol):
    async def add(self, note: Note) -> None: ...

    async def get(self, note_id: NoteId) -> Note | None: ...
