from adapters.out.in_memory.distill.note_document_parser import (
    MarkdownNoteDocumentParser,
)
from domain.distill.value_objects import NoteContent


async def test_leading_block_markers_strip_before_matching() -> None:
    parser = MarkdownNoteDocumentParser()

    assert (
        await parser.resolves(NoteContent(value="# TCP Handshake"), "TCP Handshake")
        is True
    )


async def test_whitespace_runs_collapse_before_matching() -> None:
    parser = MarkdownNoteDocumentParser()

    assert (
        await parser.resolves(
            NoteContent(value="Connections are\nestablished"),
            "Connections are established",
        )
        is True
    )
