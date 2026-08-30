from collections.abc import AsyncIterator

from application.capture.value_objects import ConfidenceAssessment, Transcript


class DeterministicReplyGenerationAdapter:
    def generate(
        self,
        transcript: Transcript,  # pyright: ignore[reportUnusedParameter]
        assessment: ConfidenceAssessment,  # pyright: ignore[reportUnusedParameter]
    ) -> AsyncIterator[str]:
        raise NotImplementedError
