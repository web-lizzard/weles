from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field

from domain.remember.due_partition import DuePartition
from domain.remember.value_objects import Grade


class DuePartitionDTO(BaseModel):
    total: int = 0
    not_yet_seen: int = 0
    seen_still_owed: int = 0
    ripe_outside_sitting: int = 0

    @classmethod
    def from_domain(cls, partition: DuePartition) -> Self:
        return cls(
            total=partition.total,
            not_yet_seen=partition.not_yet_seen,
            seen_still_owed=partition.seen_still_owed,
            ripe_outside_sitting=partition.ripe_outside_sitting,
        )


class DueCountDTO(BaseModel):
    due: DuePartitionDTO = Field(default_factory=DuePartitionDTO)


class NothingDueDTO(BaseModel):
    kind: Literal["nothing_due"] = "nothing_due"


class PresentedCardDTO(BaseModel):
    sitting_id: UUID
    card_id: UUID | None
    front: str | None
    sitting_complete: bool
    outstanding_count: int = 0
    due: DuePartitionDTO = Field(default_factory=DuePartitionDTO)


class SittingOpenedDTO(PresentedCardDTO):
    kind: Literal["opened"] = "opened"


class SittingResumedDTO(PresentedCardDTO):
    kind: Literal["resumed"] = "resumed"


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
    outstanding_count: int = 0
    next_card_id: UUID | None
    next_front: str | None
    due: DuePartitionDTO = Field(default_factory=DuePartitionDTO)
