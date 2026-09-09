from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, model_validator


class Grade(StrEnum):
    FORGOT = "forgot"
    HARD = "hard"
    GOOD = "good"
    EASY = "easy"


FINISHING_GRADES: frozenset[Grade] = frozenset({Grade.GOOD, Grade.EASY})


class SittingId(BaseModel, frozen=True):
    value: UUID

    @classmethod
    def new(cls) -> "SittingId":
        return cls(value=uuid4())


class CardId(BaseModel, frozen=True):
    value: UUID


class SchedulerAlgorithm(StrEnum):
    """Named on SchedulerStamp. Domain compares stamps; it does not run algorithms."""

    FSRS = "fsrs"


class SchedulerStamp(BaseModel, frozen=True):
    """Which scheduler produced a memoized SchedulingState.

    Compared whole to Scheduler.stamp(). Mismatch means the blob is stale
    and must be rebuilt from the review log. algorithm is a closed id;
    parameter_version is adapter-reported (library/defaults pin), not an enum.
    """

    algorithm: SchedulerAlgorithm
    parameter_version: str


class OpaqueSchedulerState(BaseModel, frozen=True):
    """Scheduler-private card memory. The domain never reads payload keys.

    The mapping is what an adapter round-trips through its library.
    A due key inside it is ignored; SchedulingState.due_at is the
    indexed field. Encoding for a store is an adapter concern, not
    this type's.
    """

    payload: dict[str, object]


class ShowingLimit(BaseModel, frozen=True):
    """Max times a card may be shown in one sitting before it counts finished.

    Completes a card together with a Good-or-better grade. Frozen on
    Sitting at open from settings (sitting_max_showings). Must be >= 1.
    """

    value: int

    @model_validator(mode="after")
    def _validate_positive(self) -> "ShowingLimit": ...
