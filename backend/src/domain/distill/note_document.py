from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from domain.distill.note_format import MARKDOWN, NoteFormat
from domain.distill.value_objects import Anchor, NoteContent


class AnchorPrecision(StrEnum):
    EXACT = "exact"
    BLOCK = "block"


class NoteBlock(BaseModel, frozen=True):
    index: int
    text: str


class AnchorLocation(BaseModel, frozen=True):
    block_index: int
    start: int
    end: int
    precision: AnchorPrecision


class NoteDocument(BaseModel, frozen=True):
    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    blocks: list[NoteBlock]
    note_format: NoteFormat

    @classmethod
    def of(
        cls,
        content: NoteContent,
        note_format: NoteFormat = MARKDOWN,
    ) -> "NoteDocument":
        _ = content
        _ = note_format
        raise NotImplementedError

    def locate(self, anchor: Anchor) -> AnchorLocation | None:
        _ = anchor
        raise NotImplementedError
