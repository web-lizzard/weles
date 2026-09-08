from typing import Protocol

from pydantic import BaseModel


class NormalizedText(BaseModel, frozen=True):
    value: str
    offsets: tuple[int, ...]


class NoteFormat(Protocol):
    def blocks(self, content: str) -> list[str]: ...

    def normalize(self, text: str) -> NormalizedText: ...


class MarkdownNoteFormat:
    def blocks(self, content: str) -> list[str]:
        _ = content
        raise NotImplementedError

    def normalize(self, text: str) -> NormalizedText:
        _ = text
        raise NotImplementedError


MARKDOWN = MarkdownNoteFormat()
