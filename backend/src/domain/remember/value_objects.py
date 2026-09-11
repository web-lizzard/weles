from datetime import timedelta
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, model_validator

from domain.remember.exceptions import (
    InvalidResumeHorizonError,
    InvalidShowingLimitError,
)


class Grade(StrEnum):
    FORGOT = "forgot"
    HARD = "hard"
    GOOD = "good"
    EASY = "easy"


class Rejected(StrEnum):
    REJECTED = "rejected"


ReviewOutcome = Grade | Rejected

FINISHING_OUTCOMES: frozenset[ReviewOutcome] = frozenset(
    {Grade.GOOD, Grade.EASY, Rejected.REJECTED}
)


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
    def _validate_positive(self) -> "ShowingLimit":
        if self.value < 1:
            raise InvalidShowingLimitError
        return self


MIN_RESUME_HORIZON = timedelta(days=1)
"""Planned Settings default for ResumeHorizon. Not a type floor; /plan wires it."""


class ResumeHorizon(BaseModel, frozen=True):
    """How long a sitting stays offered for silent return.

    Snapshotted on Sitting at open from settings, same as ShowingLimit.
    Must be strictly positive. Compose wraps settings once; later
    commands never read env. Default duration is MIN_RESUME_HORIZON
    in Settings (plan), not this validator.
    """

    value: timedelta

    @model_validator(mode="after")
    def _validate_positive(self) -> "ResumeHorizon":
        if self.value <= timedelta(0):
            raise InvalidResumeHorizonError
        return self
