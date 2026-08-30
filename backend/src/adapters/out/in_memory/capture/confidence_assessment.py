from application.capture.value_objects import (
    ConfidenceAssessment,
    ConfidencePoint,
    ConfidencePointKind,
    Transcript,
)
from domain.capture.value_objects import MessageRole


class DeterministicConfidenceAssessmentAdapter:
    async def assess(self, transcript: Transcript) -> ConfidenceAssessment:
        user_entries = [entry for entry in transcript if entry.role == MessageRole.USER]
        if not user_entries:
            return ConfidenceAssessment(points=[])

        latest = user_entries[-1]
        return ConfidenceAssessment(
            points=[
                ConfidencePoint(
                    kind=ConfidencePointKind.SOLID,
                    note=f"You've articulated: {latest.content.value.strip()}",
                ),
                ConfidencePoint(
                    kind=ConfidencePointKind.SHAKY,
                    note=f"The details behind: {latest.content.value.strip()}",
                ),
            ]
        )
