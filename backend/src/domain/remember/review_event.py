from datetime import datetime

from pydantic import BaseModel

from domain.remember.value_objects import CardId, ReviewOutcome, SittingId


class ReviewEvent(BaseModel, frozen=True):
    card_id: CardId
    reviewed_at: datetime
    outcome: ReviewOutcome
    sitting_id: SittingId
