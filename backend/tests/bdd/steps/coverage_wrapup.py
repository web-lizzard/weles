"""Step definitions for coverage wrap-up acceptance scenarios."""

from bdd.steps.capture import CaptureFlowContext
from integration.support.in_memory_capture import (
    InMemoryCaptureComposition,
)
from pytest_bdd import given, then

from application.capture.value_objects import (
    ConfidenceAssessment,
    ConfidencePoint,
    ConfidencePointKind,
    Transcript,
)


class _AllSolidConfidenceAssessmentAdapter:
    async def assess(self, transcript: Transcript) -> ConfidenceAssessment:
        _ = transcript
        return ConfidenceAssessment(
            points=[
                ConfidencePoint(
                    kind=ConfidencePointKind.SOLID,
                    note="Topic appears fully covered",
                ),
            ],
            coverage_confidence=1.0,
        )


@given("the confidence assessment reports full coverage")
def confidence_assessment_reports_full_coverage(
    capture_composition: InMemoryCaptureComposition,
) -> None:
    capture_composition.confidence_assessment = _AllSolidConfidenceAssessmentAdapter()


@then("the done event coverage confidence is fully covered")
def done_event_coverage_is_fully_covered(
    capture_flow_context: CaptureFlowContext,
) -> None:
    done_events = [
        event for event in capture_flow_context.reply_events if event["type"] == "done"
    ]
    assert done_events, "expected a done event"
    coverage = done_events[-1]["coverage_confidence"]
    assert isinstance(coverage, (int, float))
    assert coverage >= 1


@then("the follow-up message succeeds with a done event")
def follow_up_message_succeeds_with_done_event(
    capture_flow_context: CaptureFlowContext,
) -> None:
    done_events = [
        event for event in capture_flow_context.reply_events if event["type"] == "done"
    ]
    assert done_events, "expected a done event"
    last_done = done_events[-1]
    assert str(last_done.get("content", "")) != ""
