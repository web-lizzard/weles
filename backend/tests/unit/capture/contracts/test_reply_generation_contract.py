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
    ReplyTextChunk,
    TranscriptEntry,
)
from domain.capture.value_objects import MessageContent, MessageRole

_IMPLEMENTATIONS: list[Callable[[], ReplyGenerationPort]] = [
    DeterministicReplyGenerationAdapter,
]


@pytest.mark.parametrize("make_adapter", _IMPLEMENTATIONS, ids=["deterministic"])
async def test_generate_yields_chunks_that_join_into_a_nonempty_reply(
    make_adapter: Callable[[], ReplyGenerationPort],
) -> None:
    adapter = make_adapter()
    transcript = [
        TranscriptEntry(
            role=MessageRole.USER,
            content=MessageContent(value="Explain TCP handshakes"),
        )
    ]
    assessment = ConfidenceAssessment(
        points=[
            ConfidencePoint(kind=ConfidencePointKind.SOLID, note="knows the basics"),
            ConfidencePoint(kind=ConfidencePointKind.SHAKY, note="retransmission"),
        ],
        coverage_confidence=0.0,
    )

    chunks = [chunk async for chunk in adapter.generate(transcript, assessment)]

    assert chunks
    reply_chunks = [chunk for chunk in chunks if isinstance(chunk, ReplyTextChunk)]
    assert len(reply_chunks) == len(chunks)
    assert "".join(chunk.text for chunk in reply_chunks).strip() != ""
