import copy
from uuid import UUID

from domain.capture.note import Note
from domain.capture.value_objects import NoteId


class InMemoryNoteRepository:
    def __init__(self) -> None:
        self._notes: dict[UUID, Note] = {}

    async def add(self, _note: Note) -> None:
        raise NotImplementedError

    async def get(self, _note_id: NoteId) -> Note | None:
        raise NotImplementedError

    def snapshot(self) -> dict[UUID, Note]:
        return copy.deepcopy(self._notes)

    def restore(self, snapshot: dict[UUID, Note]) -> None:
        self._notes = copy.deepcopy(snapshot)
