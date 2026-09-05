import re

from domain.distill.value_objects import NoteContent

_INLINE_EMPHASIS_CHARS = ("*", "_", "`")
_LEADING_MARKER_PATTERN = re.compile(r"^(?:[#>+-]+|\d+[.)])\s*")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_BLOCK_SEPARATOR_PATTERN = re.compile(r"\n\s*\n")


class MarkdownNoteDocumentParser:
    async def resolves(self, content: NoteContent, quote: str) -> bool:
        normalized_quote = _normalize(quote)
        if not normalized_quote:
            return False
        return any(
            normalized_quote in _normalize(block) for block in _blocks(content.value)
        )


def _blocks(content: str) -> list[str]:
    return [block for block in _BLOCK_SEPARATOR_PATTERN.split(content) if block.strip()]


def _normalize(text: str) -> str:
    text = _LEADING_MARKER_PATTERN.sub("", text.strip())
    for char in _INLINE_EMPHASIS_CHARS:
        text = text.replace(char, "")
    return _WHITESPACE_PATTERN.sub(" ", text).strip()
