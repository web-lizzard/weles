from enum import StrEnum

from pydantic import BaseModel, field_validator, model_validator

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

    @field_validator("note", mode="before")
    @classmethod
    def _canonicalize_note(cls, note: object) -> object:
        if isinstance(note, str):
            return note.strip()
        return note

    @model_validator(mode="after")
    def _validate_note(self) -> "ConfidencePoint":
        if not self.note:
            raise EmptyConfidencePointError
        return self


class ConfidenceAssessment(BaseModel, frozen=True):
    points: list[ConfidencePoint]
