from datetime import datetime
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel

from domain.distill.value_objects import NoteId


class CardListItemDTO(BaseModel):
    card_id: UUID
    front: str
    back: str
    anchor_quote: str
    created_at: datetime


class ListCardsForNoteQueryPort(Protocol):
    async def list_cards_for_note(self, note_id: NoteId) -> list[CardListItemDTO]: ...
