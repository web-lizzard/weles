from datetime import datetime

from pydantic import BaseModel

from domain.remember.value_objects import CardId, ReviewEventPayload, SittingId


class ReviewEvent(BaseModel, frozen=True):
    card_id: CardId
    reviewed_at: datetime
    payload: ReviewEventPayload
    sitting_id: SittingId
