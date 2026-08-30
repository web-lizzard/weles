from application.capture.value_objects import ConfidenceAssessment, Transcript


class DeterministicConfidenceAssessmentAdapter:
    async def assess(
        self,
        transcript: Transcript,  # pyright: ignore[reportUnusedParameter]
    ) -> ConfidenceAssessment:
        raise NotImplementedError
