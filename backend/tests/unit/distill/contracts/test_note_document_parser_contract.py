from collections.abc import Callable

import pytest

from adapters.out.in_memory.distill.note_document_parser import (
    MarkdownNoteDocumentParser,
)
from application.distill.ports import NoteDocumentParser
from domain.distill.value_objects import NoteContent

_IMPLEMENTATIONS: list[Callable[[], NoteDocumentParser]] = [
    MarkdownNoteDocumentParser,
]

_NOTE = NoteContent(
    value=(
        "# TCP Handshake\n"
        "\n"
        "Connections are established\n"
        "via a three-way handshake.\n"
        "\n"
        "The client sends a **SYN** packet and waits for `SYN-ACK`.\n"
        "\n"
        "The device replies within a bounded window.\n"
    )
)


@pytest.mark.parametrize("make_parser", _IMPLEMENTATIONS, ids=["markdown"])
@pytest.mark.parametrize(
    "quote",
    [
        pytest.param(
            "The device replies within a bounded window.",
            id="verbatim",
        ),
        pytest.param(
            "Connections are established via a three-way handshake.",
            id="reflowed-across-a-line-wrap",
        ),
        pytest.param(
            "The client sends a SYN packet and waits for SYN-ACK.",
            id="through-emphasis-and-code-markers",
        ),
        pytest.param("TCP Handshake", id="heading-text-without-its-marker"),
    ],
)
async def test_resolves_true_for_a_quote_matching_a_single_normalized_block(
    make_parser: Callable[[], NoteDocumentParser],
    quote: str,
) -> None:
    parser = make_parser()

    assert await parser.resolves(_NOTE, quote) is True


@pytest.mark.parametrize("make_parser", _IMPLEMENTATIONS, ids=["markdown"])
@pytest.mark.parametrize(
    "quote",
    [
        pytest.param(
            "The server drops the connection immediately.",
            id="fabricated",
        ),
        pytest.param(
            "via a three-way handshake. The client sends",
            id="spans-two-blocks",
        ),
        pytest.param("", id="empty"),
        pytest.param("   ", id="whitespace-only"),
    ],
)
async def test_resolves_false_when_no_single_block_matches(
    make_parser: Callable[[], NoteDocumentParser],
    quote: str,
) -> None:
    parser = make_parser()

    assert await parser.resolves(_NOTE, quote) is False


@pytest.mark.parametrize("make_parser", _IMPLEMENTATIONS, ids=["markdown"])
async def test_leading_block_markers_strip_before_matching(
    make_parser: Callable[[], NoteDocumentParser],
) -> None:
    parser = make_parser()

    assert (
        await parser.resolves(NoteContent(value="# TCP Handshake"), "TCP Handshake")
        is True
    )


@pytest.mark.parametrize("make_parser", _IMPLEMENTATIONS, ids=["markdown"])
async def test_whitespace_runs_collapse_before_matching(
    make_parser: Callable[[], NoteDocumentParser],
) -> None:
    parser = make_parser()

    assert (
        await parser.resolves(
            NoteContent(value="Connections are\nestablished"),
            "Connections are established",
        )
        is True
    )
