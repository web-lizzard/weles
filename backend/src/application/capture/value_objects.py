from enum import StrEnum

from pydantic import BaseModel, model_validator

from application.capture.exceptions import EmptyConfidencePointError
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

    @model_validator(mode="after")
    def _validate_note(self) -> "ConfidencePoint":
        if not self.note.strip():
            raise EmptyConfidencePointError
        return self


class ConfidenceAssessment(BaseModel, frozen=True):
    points: list[ConfidencePoint]
