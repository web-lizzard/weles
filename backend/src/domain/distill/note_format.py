import re
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class NormalizedText(BaseModel, frozen=True):
    value: str
    offsets: tuple[int, ...]


@runtime_checkable
class NoteFormat(Protocol):
    def blocks(self, content: str) -> list[str]: ...

    def normalize(self, text: str) -> NormalizedText: ...


class MarkdownNoteFormat:
    def blocks(self, content: str) -> list[str]:
        return [
            block.strip("\n")
            for block in _BLOCK_SEPARATOR.split(content)
            if block.strip()
        ]

    def normalize(self, text: str) -> NormalizedText:
        body_start, body_end = _trimmed_bounds(text)
        cursor = _after_leading_marker(text, body_start, body_end)
        kept: list[str] = []
        offsets: list[int] = []
        pending_space_at: int | None = None
        while cursor < body_end:
            char = text[cursor]
            if char in _INLINE_EMPHASIS_CHARS:
                cursor += 1
                continue
            if char.isspace():
                if kept:
                    pending_space_at = cursor
                cursor += 1
                continue
            if pending_space_at is not None:
                kept.append(" ")
                offsets.append(pending_space_at)
                pending_space_at = None
            kept.append(char)
            offsets.append(cursor)
            cursor += 1
        return NormalizedText(value="".join(kept), offsets=tuple(offsets))


MARKDOWN = MarkdownNoteFormat()

_BLOCK_SEPARATOR = re.compile(r"\n\s*\n")
_INLINE_EMPHASIS_CHARS = frozenset("*_`")
_LEADING_MARKER = re.compile(r"^(?:[#>+-]+|\d+[.)])\s*")


def _trimmed_bounds(text: str) -> tuple[int, int]:
    start = 0
    end = len(text)
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _after_leading_marker(text: str, start: int, end: int) -> int:
    if start >= end:
        return start
    match = _LEADING_MARKER.match(text[start:end])
    if match is None:
        return start
    return start + match.end()
