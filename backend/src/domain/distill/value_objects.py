from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel

NOTE_CONTENT_MAX_LENGTH = 20000


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


class DistillationStatus(StrEnum):
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
