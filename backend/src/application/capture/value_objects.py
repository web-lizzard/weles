from enum import StrEnum

from pydantic import BaseModel

from domain.capture.value_objects import MessageContent, MessageRole


class ConfidencePointKind(StrEnum):
    SOLID = "solid"
    SHAKY = "shaky"


class TranscriptEntry(BaseModel, frozen=True):
    role: MessageRole
    content: MessageContent


Transcript = list[TranscriptEntry]


class ConfidencePoint(BaseModel, frozen=True):
    kind: ConfidencePointKind
    note: str


class ConfidenceAssessment(BaseModel, frozen=True):
    points: list[ConfidencePoint]
