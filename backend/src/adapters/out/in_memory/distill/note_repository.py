import copy
from uuid import UUID

from domain.distill.note import Note
from domain.distill.value_objects import NoteId


class InMemoryNoteRepository:
    def __init__(self) -> None:
        self._notes: dict[UUID, Note] = {}

    async def save(self, note: Note) -> None:
        self._notes[note.id.value] = note

    async def get(self, note_id: NoteId) -> Note | None:
        return self._notes.get(note_id.value)

    def snapshot(self) -> dict[UUID, Note]:
        return copy.deepcopy(self._notes)

    def restore(self, snapshot: dict[UUID, Note]) -> None:
        self._notes = copy.deepcopy(snapshot)
