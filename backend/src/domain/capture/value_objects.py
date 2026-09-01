from enum import StrEnum
from math import isfinite, sqrt
from uuid import UUID, uuid4

from pydantic import BaseModel, field_validator, model_validator

from domain.capture.exceptions import (
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


class MessageRole(StrEnum):
    USER = "user"
    AGENT = "agent"


class SessionStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


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

    def cosine_similarity(self, other: "Embedding") -> SimilarityScore:
        if len(self.values) != len(other.values):
            raise EmbeddingDimensionMismatchError
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
