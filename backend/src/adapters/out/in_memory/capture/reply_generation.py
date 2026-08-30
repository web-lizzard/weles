import asyncio
from collections.abc import AsyncIterator

from application.capture.value_objects import (
    ConfidenceAssessment,
    ConfidencePointKind,
    Transcript,
)

_CHUNK_SIZE = 12
_CHUNK_DELAY_SECONDS = 0.01
_DEFAULT_SOLID = "what you've said so far"
_DEFAULT_SHAKY = "the parts you haven't unpacked yet"


class DeterministicReplyGenerationAdapter:
    async def generate(
        self,
        transcript: Transcript,  # pyright: ignore[reportUnusedParameter]
        assessment: ConfidenceAssessment,
    ) -> AsyncIterator[str]:
        solid = next(
            (
                point.note
                for point in assessment.points
                if point.kind == ConfidencePointKind.SOLID
            ),
            _DEFAULT_SOLID,
        )
        shaky = next(
            (
                point.note
                for point in assessment.points
                if point.kind == ConfidencePointKind.SHAKY
            ),
            _DEFAULT_SHAKY,
        )
        reply = f"You've got a handle on: {solid}. Let's dig into: {shaky}."

        for start in range(0, len(reply), _CHUNK_SIZE):
            yield reply[start : start + _CHUNK_SIZE]
            await asyncio.sleep(_CHUNK_DELAY_SECONDS)
