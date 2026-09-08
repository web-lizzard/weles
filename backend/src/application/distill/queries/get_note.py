from datetime import datetime
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel

from domain.distill.value_objects import NoteId


class NoteDetailTopicDTO(BaseModel):
    id: UUID
    label: str


class NoteDetailTagDTO(BaseModel):
    id: UUID
    label: str


class NoteBlockDTO(BaseModel):
    index: int
    text: str


class NoteDetailDTO(BaseModel):
    note_id: UUID
    topic: NoteDetailTopicDTO
    content: str
    blocks: list[NoteBlockDTO]
    tags: list[NoteDetailTagDTO]
    distillation_status: str
    approved_at: datetime
    created_at: datetime
    updated_at: datetime


class GetNoteQueryPort(Protocol):
    async def get_note(self, note_id: NoteId) -> NoteDetailDTO: ...
