from collections.abc import Callable

import pytest

from adapters.out.in_memory.capture.reply_generation import (
    DeterministicReplyGenerationAdapter,
)
from application.capture.ports import ReplyGenerationPort
from application.capture.value_objects import (
    ConfidenceAssessment,
    ConfidencePoint,
    ConfidencePointKind,
    DraftContentChunk,
    ReplyChunk,
    ReplyChunkKind,
    ReplyTextChunk,
    TranscriptEntry,
)
from domain.capture.value_objects import MessageContent, MessageRole

_IMPLEMENTATIONS: list[Callable[[], ReplyGenerationPort]] = [
    DeterministicReplyGenerationAdapter,
]

_DRAFTING_CONFIRMATION = "that's all"


def _conversational_transcript() -> list[TranscriptEntry]:
    return [
        TranscriptEntry(
            role=MessageRole.USER,
            content=MessageContent(value="Explain TCP handshakes"),
        )
    ]


def _drafting_transcript() -> list[TranscriptEntry]:
    return [
        TranscriptEntry(
            role=MessageRole.USER,
            content=MessageContent(value="Let's talk through TCP handshakes"),
        ),
        TranscriptEntry(
            role=MessageRole.AGENT,
            content=MessageContent(value="What do you know about the SYN packet?"),
        ),
        TranscriptEntry(
            role=MessageRole.USER,
            content=MessageContent(value=_DRAFTING_CONFIRMATION),
        ),
    ]


def _default_assessment() -> ConfidenceAssessment:
    return ConfidenceAssessment(
        points=[
            ConfidencePoint(kind=ConfidencePointKind.SOLID, note="knows the basics"),
            ConfidencePoint(kind=ConfidencePointKind.SHAKY, note="retransmission"),
        ],
        coverage_confidence=0.0,
    )


def _assert_drafting_chunk_order(chunks: list[ReplyChunk]) -> None:
    kinds = [chunk.kind for chunk in chunks]

    topic_indices = [
        index for index, kind in enumerate(kinds) if kind == ReplyChunkKind.TOPIC
    ]
    assert len(topic_indices) == 1
    topic_index = topic_indices[0]

    assert topic_index >= 1
    assert all(kind == ReplyChunkKind.REPLY for kind in kinds[:topic_index])

    note_indices = [
        index for index, kind in enumerate(kinds) if kind == ReplyChunkKind.NOTE
    ]
    first_note_index = note_indices[0] if note_indices else len(kinds)
    middle_kinds = kinds[topic_index + 1 : first_note_index]
    assert all(kind == ReplyChunkKind.TAG for kind in middle_kinds)

    if note_indices:
        assert all(kind == ReplyChunkKind.NOTE for kind in kinds[first_note_index:])
        for index in range(first_note_index + 1, len(kinds)):
            assert kinds[index] not in (ReplyChunkKind.TOPIC, ReplyChunkKind.TAG)

    note_text = "".join(
        chunk.text for chunk in chunks if isinstance(chunk, DraftContentChunk)
    )
    assert note_text.strip() != ""


@pytest.mark.parametrize("make_adapter", _IMPLEMENTATIONS, ids=["deterministic"])
async def test_generate_yields_chunks_that_join_into_a_nonempty_reply(
    make_adapter: Callable[[], ReplyGenerationPort],
) -> None:
    adapter = make_adapter()
    chunks = [
        chunk
        async for chunk in adapter.generate(
            _conversational_transcript(), _default_assessment()
        )
    ]

    assert chunks
    reply_chunks = [chunk for chunk in chunks if isinstance(chunk, ReplyTextChunk)]
    assert len(reply_chunks) == len(chunks)
    assert "".join(chunk.text for chunk in reply_chunks).strip() != ""


@pytest.mark.parametrize("make_adapter", _IMPLEMENTATIONS, ids=["deterministic"])
async def test_generate_yields_only_reply_chunks_for_conversational_transcript(
    make_adapter: Callable[[], ReplyGenerationPort],
) -> None:
    adapter = make_adapter()
    chunks = [
        chunk
        async for chunk in adapter.generate(
            _conversational_transcript(), _default_assessment()
        )
    ]

    assert chunks
    assert all(isinstance(chunk, ReplyTextChunk) for chunk in chunks)


@pytest.mark.parametrize("make_adapter", _IMPLEMENTATIONS, ids=["deterministic"])
async def test_generate_yields_drafting_chunks_in_contract_order(
    make_adapter: Callable[[], ReplyGenerationPort],
) -> None:
    adapter = make_adapter()
    chunks = [
        chunk
        async for chunk in adapter.generate(
            _drafting_transcript(), _default_assessment()
        )
    ]

    assert chunks
    _assert_drafting_chunk_order(chunks)
