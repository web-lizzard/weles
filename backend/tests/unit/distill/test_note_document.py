from domain.distill.note_document import AnchorPrecision, NoteDocument
from domain.distill.note_format import NormalizedText
from domain.distill.value_objects import Anchor, NoteContent


class _IdentityFormat:
    def blocks(self, content: str) -> list[str]:
        return [content] if content else []

    def normalize(self, text: str) -> NormalizedText:
        return NormalizedText(value=text, offsets=tuple(range(len(text))))


def test_locate_returns_exact_span_equal_to_a_plain_paragraph_quote() -> None:
    quote = "The device replies within a bounded window."
    document = NoteDocument.of(NoteContent(value=quote))

    location = document.locate(Anchor(quote=quote))

    assert location is not None
    assert location.precision is AnchorPrecision.EXACT
    block = document.blocks[location.block_index]
    assert block.text[location.start : location.end] == quote


def test_locate_returns_exact_span_covering_emphasis_markup() -> None:
    raw = "The client sends a **SYN** packet and waits for `SYN-ACK`."
    document = NoteDocument.of(NoteContent(value=raw))

    location = document.locate(
        Anchor(quote="The client sends a SYN packet and waits for SYN-ACK.")
    )

    assert location is not None
    assert location.precision is AnchorPrecision.EXACT
    span = document.blocks[location.block_index].text[location.start : location.end]
    assert "**SYN**" in span
    assert "`SYN-ACK`" in span


def test_locate_degrades_a_heading_match_and_reports_the_second_block() -> None:
    heading = NoteDocument.of(NoteContent(value="# TCP Handshake"))
    later = NoteDocument.of(
        NoteContent(value="# TCP\n\nThe **handshake** begins here.")
    )

    heading_location = heading.locate(Anchor(quote="TCP Handshake"))
    later_location = later.locate(Anchor(quote="handshake begins here"))

    assert heading_location is not None
    assert heading_location.precision is AnchorPrecision.BLOCK
    assert heading_location.start == 0
    assert heading_location.end == len(heading.blocks[0].text)
    assert later_location is not None
    assert later_location.block_index == 1


def test_locate_keeps_an_exact_span_when_only_the_first_word_is_emphasized() -> None:
    # R1-F1: a match at the start of a block must not mark the remainder.
    content = "lead in\n\n**aaa** and aaaaaaaaaaaaaaaa"
    document = NoteDocument.of(NoteContent(value=content))

    location = document.locate(Anchor(quote="aaa"))

    assert location is not None
    block = document.blocks[location.block_index]
    span = block.text[location.start : location.end]
    assert location.precision is AnchorPrecision.EXACT
    assert "aaaaaaaaaaaaaaaa" not in span
    assert "aaa" in span.replace("*", "")


def test_locate_returns_none_when_unresolved_and_ignores_format_syntax() -> None:
    document = NoteDocument.of(
        NoteContent(value="The device replies within a bounded window.")
    )
    fake = NoteDocument.of(
        NoteContent(value="plain source fragment"),
        note_format=_IdentityFormat(),
    )

    missing = Anchor(quote="The server drops the connection immediately.")
    assert document.locate(missing) is None
    assert document.locate(Anchor(quote="*")) is None
    location = fake.locate(Anchor(quote="plain source fragment"))

    assert location is not None
    assert location.precision is AnchorPrecision.EXACT
    assert fake.blocks[0].text[location.start : location.end] == "plain source fragment"
