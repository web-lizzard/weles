from application.distill.queries.get_note import (
    NoteDetailDTO,
    NoteDetailTagDTO,
    NoteDetailTopicDTO,
)
from domain.distill.exceptions import DistillNoteNotFoundError
from domain.distill.ports import NoteRepository
from domain.distill.value_objects import NoteId


class InMemoryGetNoteQueryAdapter:
    def __init__(self, note_repository: NoteRepository) -> None:
        self._note_repository: NoteRepository = note_repository

    async def get_note(self, note_id: NoteId) -> NoteDetailDTO:
        note = await self._note_repository.get(note_id)
        if note is None:
            raise DistillNoteNotFoundError
        return NoteDetailDTO(
            note_id=note.id.value,
            topic=NoteDetailTopicDTO(id=note.topic.id, label=note.topic.label),
            content=note.content.value,
            blocks=[],
            tags=[NoteDetailTagDTO(id=tag.id, label=tag.label) for tag in note.tags],
            distillation_status=note.distillation_status,
            approved_at=note.approved_at,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )
