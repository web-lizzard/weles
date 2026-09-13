from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator

from domain.distill.exceptions import (
    CardSideTooLongError,
    DistillEmptyNoteContentError,
    DistillNoteContentTooLongError,
    EmptyAnchorError,
    EmptyCardSideError,
)

NOTE_CONTENT_MAX_LENGTH = 20000
CARD_SIDE_MAX_LENGTH = 2000
ANCHOR_MAX_LENGTH = 4000


class NoteId(BaseModel, frozen=True):
    value: UUID


class SessionId(BaseModel, frozen=True):
    value: UUID


class TopicSnapshot(BaseModel, frozen=True):
    id: UUID
    label: str


class TagSnapshot(BaseModel, frozen=True):
    id: UUID
    label: str


class NoteContent(BaseModel, frozen=True):
    value: str

    @field_validator("value", mode="before")
    @classmethod
    def _canonicalize_value(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def _validate_value(self) -> "NoteContent":
        if not self.value:
            raise DistillEmptyNoteContentError
        if len(self.value) > NOTE_CONTENT_MAX_LENGTH:
            raise DistillNoteContentTooLongError
        return self


class DistillationStatus(StrEnum):
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class CardId(BaseModel, frozen=True):
    value: UUID


class CardSide(BaseModel, frozen=True):
    value: str

    @field_validator("value", mode="before")
    @classmethod
    def _canonicalize_value(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def _validate_value(self) -> "CardSide":
        if not self.value:
            raise EmptyCardSideError
        if len(self.value) > CARD_SIDE_MAX_LENGTH:
            raise CardSideTooLongError
        return self


class Anchor(BaseModel, frozen=True):
    quote: str

    @field_validator("quote", mode="before")
    @classmethod
    def _canonicalize_quote(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def _validate_quote(self) -> "Anchor":
        if not self.quote:
            raise EmptyAnchorError
        if len(self.quote) > ANCHOR_MAX_LENGTH:
            raise CardSideTooLongError
        return self


class DiscardReason(StrEnum):
    """Why a card was discarded. Fixed by the domain; a model never authors a
    reason, only the `Discard.detail` that accompanies one."""

    UNGROUNDED = "ungrounded"
    OVERSIZED = "oversized"
    USER_AUDIT = "user_audit"
    LOW_QUALITY = "low_quality"
    """Review judged the card below the passing grade; `detail` carries the
    model's reasoning."""
    DUPLICATE = "duplicate"
    """Merge judged the card to say the same thing as a card that survived."""


class DistillPhase(StrEnum):
    """The phases of one card-generation run, in the only order the flow's
    graph permits. Never persisted: a run lives within one invocation.

    Two review phases, not one — the flow is acyclic, so the review after
    regeneration cannot be a return to the first review. `MERGING` is the only
    terminal phase.
    """

    GENERATING = "generating"
    REVIEWING = "reviewing"
    REGENERATING = "regenerating"
    REVIEWING_REPLACEMENTS = "reviewing_replacements"
    MERGING = "merging"


class AnchorResolution(StrEnum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


class Discard(BaseModel, frozen=True):
    reason: DiscardReason
    detail: str | None
    discarded_at: datetime


class CardLengthPolicy(BaseModel, frozen=True):
    front_max: int
    back_max: int

    def breach(self, front: CardSide, back: CardSide) -> str | None:
        if len(front.value) > self.front_max:
            return f"front exceeds front_max={self.front_max}"
        if len(back.value) > self.back_max:
            return f"back exceeds back_max={self.back_max}"
        return None


class CardProposal(BaseModel, frozen=True):
    """One card as a model proposed it, before any domain check.

    Raw strings on purpose. An oversized or ungrounded proposal is a discard
    the domain records, not a malformed answer — so nothing here may refuse
    one at validation, or the whole model answer would fail with it.
    """

    front: str
    back: str
    quote: str


class CandidateRef(BaseModel, frozen=True):
    """How a run and the model refer to one candidate card: a short label the
    run mints, never a `CardId`. Unique within one run."""

    value: str


class ReviewGrade(StrEnum):
    """Review's judgment of one card, on an ordered scale — worst first.

    Declaration order is the order. Whether a grade passes is the domain's
    rule (`passes`), never the model's.
    """

    POOR = "poor"
    WEAK = "weak"
    SOUND = "sound"
    STRONG = "strong"

    @property
    def rank(self) -> int:
        """Position on the scale, higher is better. What merge compares."""
        return list(ReviewGrade).index(self)

    @property
    def passes(self) -> bool:
        """Whether a card with this grade is accepted."""
        return self in (ReviewGrade.SOUND, ReviewGrade.STRONG)


class CardVerdict(BaseModel, frozen=True):
    """Review's judgment of one candidate, with the reasoning behind it.

    `reasoning` becomes the `Discard.detail` of a card that does not pass, and
    the finding regeneration is told about.
    """

    ref: CandidateRef
    grade: ReviewGrade
    reasoning: str


class DuplicateGroup(BaseModel, frozen=True):
    """Candidates merge judged to say the same thing. The model names the
    group; which member survives is the domain's rule, not the model's."""

    refs: tuple[CandidateRef, ...]
    reasoning: str
