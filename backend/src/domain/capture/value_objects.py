from enum import StrEnum
from math import isfinite, sqrt
from uuid import UUID, uuid4

from pydantic import BaseModel, field_validator, model_validator

from domain.capture.exceptions import (
    CoverageOutOfRangeError,
    EmbeddingDimensionMismatchError,
    EmptyEmbeddingError,
    EmptyLabelError,
    EmptyMessageContentError,
    EmptyNoteContentError,
    EmptySessionTopicError,
    LabelTooLongError,
    MessageContentTooLongError,
    NoteContentTooLongError,
    SessionTopicTooLongError,
    SimilarityScoreOutOfRangeError,
    ZeroMagnitudeEmbeddingError,
)

SESSION_TOPIC_MAX_LENGTH = 200
MESSAGE_CONTENT_MAX_LENGTH = 4000
LABEL_MAX_LENGTH = 120
NOTE_CONTENT_MAX_LENGTH = 20000
SIMILARITY_SCORE_MIN = -1.0
SIMILARITY_SCORE_MAX = 1.0
COVERAGE_MIN = 0.0
COVERAGE_MAX = 1.0


class MessageRole(StrEnum):
    USER = "user"
    AGENT = "agent"


class SessionStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class CapturePhase(StrEnum):
    """Which part of the capture flow a session is in. Neither is terminal
    while the session is open (FR-02)."""

    CONVERSING = "conversing"
    DRAFTING = "drafting"


class Coverage(BaseModel, frozen=True):
    """How fully the session's topic has been covered, as the model judged it
    on one turn.

    A value object rather than a bare float because the range is a domain fact
    and the model is the one supplying it: `CoverageAssessed` carries whatever
    the model sent, and an unvalidated float would let 7.3 or a NaN through the
    tool and onto the session, where the trend arithmetic would silently
    inherit it.

    This number travels inward only. It reaches the domain as a tool result and
    is never read back out to the model — what crosses the port on the way out
    is a `CoverageReading`, a word. The float stays available as telemetry on
    the reply event, which is a different reader.
    """

    value: float

    @model_validator(mode="after")
    def _validate_value(self) -> "Coverage":
        if not isfinite(self.value):
            raise CoverageOutOfRangeError
        if not COVERAGE_MIN <= self.value <= COVERAGE_MAX:
            raise CoverageOutOfRangeError
        return self


class CoverageTrend(StrEnum):
    """Which way coverage has moved across the session's kept assessments.

    Three-valued, because coverage falls as well as rises: a user who opens new
    ground mid-session makes the topic larger, and the honest assessment of how
    much is covered drops. A two-valued reading would have to call that either
    progress or no-change, and both are wrong.

    `FLAT` is a band, not an equality. Without one, every reassessment would
    register as a direction and the trend would be noise wearing a word. The
    width of the band is the domain's constant and is what makes "the coverage
    is rising" falsifiable.

    Arithmetic, not policy. What the agent should do about a direction is
    `CoverageReading`'s; this says only which way the numbers went, and is
    unit-testable without anyone agreeing on tone.
    """

    RISING = "rising"
    FLAT = "flat"
    FALLING = "falling"


class CoverageReading(StrEnum):
    """The word that crosses the port: how the session is going, as the domain
    reads it from the level and the trend together.

    This is FR-03's policy and the reason coverage is load-bearing rather than
    telemetry. Each member is a distinct thing to be encouraging about, and each
    has prose of its own that the `coverage_trend` block speaks; a member with
    no tone of its own would not earn its place.

    Closed on purpose. A suite walks every member and asserts it has prose, so a
    reading added later cannot reach the model as a word with nothing behind it.

    `frame.md` names two of these directly — a coverage that is climbing turns
    the tone towards closing, and one that is flat and low affirms keeping the
    session open. The other two are the cases that sentence leaves out.
    """

    EARLY = "early"
    """Low, and not moving. The topic has barely been opened — keep drawing it
    out, and do not raise closing at all."""

    DEEPENING = "deepening"
    """Rising. The conversation is working; closing is becoming available and
    may be offered, not pressed."""

    WIDENING = "widening"
    """Falling. The user has opened ground that was not counted before, so the
    topic grew. Follow the new ground; do not read the drop as losing progress
    and do not push towards closing."""

    SETTLED = "settled"
    """High, and not moving. Little new is arriving — say so, and encourage
    closing the session."""


class DraftingConsent(BaseModel, frozen=True):
    """The user's expressed wish to draft. Disjoint from `ConversationRequest`."""


class ConversationRequest(BaseModel, frozen=True):
    """The user's expressed wish to return to conversation. Disjoint from
    `DraftingConsent`."""


class NoteStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    DISCARDED = "discarded"


class SessionTopic(BaseModel, frozen=True):
    value: str

    @field_validator("value", mode="before")
    @classmethod
    def _canonicalize_value(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def _validate_value(self) -> "SessionTopic":
        if not self.value:
            raise EmptySessionTopicError
        if len(self.value) > SESSION_TOPIC_MAX_LENGTH:
            raise SessionTopicTooLongError
        return self


class MessageContent(BaseModel, frozen=True):
    value: str

    @field_validator("value", mode="before")
    @classmethod
    def _canonicalize_value(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def _validate_value(self) -> "MessageContent":
        if not self.value:
            raise EmptyMessageContentError
        if len(self.value) > MESSAGE_CONTENT_MAX_LENGTH:
            raise MessageContentTooLongError
        return self


class SessionId(BaseModel, frozen=True):
    value: UUID

    @classmethod
    def new(cls) -> "SessionId":
        return cls(value=uuid4())


class MessageId(BaseModel, frozen=True):
    value: UUID

    @classmethod
    def new(cls) -> "MessageId":
        return cls(value=uuid4())


class Label(BaseModel, frozen=True):
    value: str

    @field_validator("value", mode="before")
    @classmethod
    def _canonicalize_value(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def _validate_value(self) -> "Label":
        if not self.value:
            raise EmptyLabelError
        if len(self.value) > LABEL_MAX_LENGTH:
            raise LabelTooLongError
        return self


class SimilarityScore(BaseModel, frozen=True):
    value: float

    @model_validator(mode="after")
    def _validate_value(self) -> "SimilarityScore":
        if not isfinite(self.value):
            raise SimilarityScoreOutOfRangeError
        if not SIMILARITY_SCORE_MIN <= self.value <= SIMILARITY_SCORE_MAX:
            raise SimilarityScoreOutOfRangeError
        return self


class Embedding(BaseModel, frozen=True):
    values: tuple[float, ...]
    model: str

    def cosine_similarity(self, other: "Embedding") -> SimilarityScore:
        if len(self.values) != len(other.values):
            raise EmbeddingDimensionMismatchError
        if self.values == other.values:
            _ = _scaled_to_largest_component(self.values)
            return SimilarityScore(value=SIMILARITY_SCORE_MAX)
        left = _scaled_to_largest_component(self.values)
        right = _scaled_to_largest_component(other.values)
        dot = sum(a * b for a, b in zip(left, right, strict=True))
        magnitudes = _magnitude(left) * _magnitude(right)
        return SimilarityScore(value=_clamped_to_score_range(dot / magnitudes))

    @model_validator(mode="after")
    def _validate_values(self) -> "Embedding":
        if not self.values:
            raise EmptyEmbeddingError
        return self


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
            raise EmptyNoteContentError
        if len(self.value) > NOTE_CONTENT_MAX_LENGTH:
            raise NoteContentTooLongError
        return self


class NoteId(BaseModel, frozen=True):
    value: UUID

    @classmethod
    def new(cls) -> "NoteId":
        return cls(value=uuid4())


class TopicId(BaseModel, frozen=True):
    value: UUID

    @classmethod
    def new(cls) -> "TopicId":
        return cls(value=uuid4())


class TagId(BaseModel, frozen=True):
    value: UUID

    @classmethod
    def new(cls) -> "TagId":
        return cls(value=uuid4())


def _scaled_to_largest_component(values: tuple[float, ...]) -> tuple[float, ...]:
    largest = max(abs(value) for value in values)
    if largest == 0.0:
        raise ZeroMagnitudeEmbeddingError
    return tuple(value / largest for value in values)


def _magnitude(values: tuple[float, ...]) -> float:
    return sqrt(sum(value * value for value in values))


def _clamped_to_score_range(value: float) -> float:
    return min(max(value, SIMILARITY_SCORE_MIN), SIMILARITY_SCORE_MAX)
