from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from domain.distill.note_format import MARKDOWN, NormalizedText, NoteFormat
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
        blocks = [
            NoteBlock(index=index, text=block)
            for index, block in enumerate(note_format.blocks(content.value))
        ]
        return cls(blocks=blocks, note_format=note_format)

    def locate(self, anchor: Anchor) -> AnchorLocation | None:
        quote = self.note_format.normalize(anchor.quote)
        if not quote.value:
            return None
        for block in self.blocks:
            location = _locate_in_block(block, quote, self.note_format)
            if location is not None:
                return location
        return None


def _locate_in_block(
    block: NoteBlock,
    quote: NormalizedText,
    note_format: NoteFormat,
) -> AnchorLocation | None:
    normalized = note_format.normalize(block.text)
    index = normalized.value.find(quote.value)
    if index == -1:
        return None
    last = index + len(quote.value) - 1
    start = normalized.offsets[index]
    end = normalized.offsets[last] + 1
    recovered = note_format.normalize(block.text[start:end])
    if recovered.value == quote.value and not (index == 0 and start > 0):
        return AnchorLocation(
            block_index=block.index,
            start=start,
            end=end,
            precision=AnchorPrecision.EXACT,
        )
    return AnchorLocation(
        block_index=block.index,
        start=0,
        end=len(block.text),
        precision=AnchorPrecision.BLOCK,
    )
