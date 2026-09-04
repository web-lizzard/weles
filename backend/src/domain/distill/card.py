from datetime import datetime

from pydantic import BaseModel, model_validator

from domain.distill.value_objects import (
    Anchor,
    CardId,
    CardSide,
    Discard,
    NoteId,
)


class Card(BaseModel):
    id: CardId
    note_id: NoteId
    front: CardSide
    back: CardSide
    anchor: Anchor
    discard: Discard | None
    created_at: datetime

    @model_validator(mode="after")
    def _validate_sides_differ(self) -> "Card": ...
