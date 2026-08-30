from collections.abc import Callable

import pytest

from adapters.out.in_memory.capture.confidence_assessment import (
    DeterministicConfidenceAssessmentAdapter,
)
from application.capture.ports import ConfidenceAssessmentPort
from application.capture.value_objects import ConfidencePointKind, TranscriptEntry
from domain.capture.value_objects import MessageContent, MessageRole

_IMPLEMENTATIONS: list[Callable[[], ConfidenceAssessmentPort]] = [
    DeterministicConfidenceAssessmentAdapter,
]


@pytest.mark.parametrize("make_adapter", _IMPLEMENTATIONS, ids=["deterministic"])
async def test_assess_returns_solid_and_shaky_points_for_a_transcript_with_a_user_turn(
    make_adapter: Callable[[], ConfidenceAssessmentPort],
) -> None:
    adapter = make_adapter()
    transcript = [
        TranscriptEntry(
            role=MessageRole.USER,
            content=MessageContent(value="I think TCP uses a three-way handshake"),
        )
    ]

    assessment = await adapter.assess(transcript)

    kinds = {point.kind for point in assessment.points}
    assert ConfidencePointKind.SOLID in kinds
    assert ConfidencePointKind.SHAKY in kinds
