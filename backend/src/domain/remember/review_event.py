from datetime import datetime

from pydantic import BaseModel

from domain.remember.value_objects import CardId, Grade, SittingId


class ReviewEvent(BaseModel, frozen=True):
    card_id: CardId
    reviewed_at: datetime
    grade: Grade
    sitting_id: SittingId
