from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from domain.remember.value_objects import Grade


class NothingDueDTO(BaseModel):
    kind: Literal["nothing_due"] = "nothing_due"


class PresentedCardDTO(BaseModel):
    sitting_id: UUID
    card_id: UUID | None
    front: str | None
    sitting_complete: bool


class SittingOpenedDTO(PresentedCardDTO):
    kind: Literal["opened"] = "opened"


class RevealedCardDTO(BaseModel):
    sitting_id: UUID
    card_id: UUID
    front: str
    back: str


class GradeRequestDTO(BaseModel):
    grade: Grade


class GradeAppliedDTO(BaseModel):
    sitting_id: UUID
    sitting_complete: bool
    next_card_id: UUID | None
    next_front: str | None
