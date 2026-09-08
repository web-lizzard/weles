from domain.distill.note_format import MARKDOWN


def test_blocks_split_on_blank_lines_and_drop_empty_blocks() -> None:
    content = "\n".join(
        [
            "# TCP Handshake",
            "",
            "Connections are established",
            "via a three-way handshake.",
            "",
            "",
            "The device replies within a bounded window.",
        ]
    )
    blocks = MARKDOWN.blocks(content)

    assert blocks == [
        "# TCP Handshake",
        "Connections are established\nvia a three-way handshake.",
        "The device replies within a bounded window.",
    ]


def test_normalize_strips_markup_and_maps_offsets_to_raw_characters() -> None:
    heading = MARKDOWN.normalize("# TCP Handshake")
    emphasized = MARKDOWN.normalize("The client sends a **SYN** packet.")
    wrapped = MARKDOWN.normalize("Connections are\nestablished")

    assert heading.value == "TCP Handshake"
    assert "".join(heading.value[i] for i in range(len(heading.value))) == (
        "".join("# TCP Handshake"[offset] for offset in heading.offsets)
    )
    assert emphasized.value == "The client sends a SYN packet."
    assert emphasized.offsets[emphasized.value.index("S")] == (
        "The client sends a **SYN** packet.".index("S")
    )
    assert wrapped.value == "Connections are established"
    assert len(wrapped.offsets) == len(wrapped.value)
