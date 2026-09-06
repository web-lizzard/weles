from datetime import datetime
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel


class NoteListItemDTO(BaseModel):
    note_id: UUID
    topic_label: str
    distillation_status: str
    card_count: int
    last_updated_at: datetime


class ListNotesQueryPort(Protocol):
    async def list_notes(self) -> list[NoteListItemDTO]: ...
