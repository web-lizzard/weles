from domain.distill.value_objects import NoteContent


class MarkdownNoteDocumentParser:
    async def resolves(self, _content: NoteContent, _quote: str) -> bool: ...
