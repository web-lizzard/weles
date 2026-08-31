import pytest
from pydantic import ValidationError

from application.capture.exceptions import EmptyConfidencePointError
from application.capture.value_objects import (
    ConfidenceAssessment,
    ConfidencePoint,
    ConfidencePointKind,
)


def test_confidence_point_empty_note_raises_empty_confidence_point_error() -> None:
    with pytest.raises(EmptyConfidencePointError):
        _ = ConfidencePoint(kind=ConfidencePointKind.SOLID, note="   ")


def test_R3_F3_confidence_point_stores_canonical_stripped_value() -> None:
    """R3-F3: ConfidencePoint must persist strip(note), not the raw input."""
    point = ConfidencePoint(kind=ConfidencePointKind.SOLID, note="knows basics\r")

    assert point.note == "knows basics"


@pytest.mark.parametrize("coverage_confidence", [0.0, 0.5, 1.0])
def test_confidence_assessment_accepts_coverage_confidence_within_bounds(
    coverage_confidence: float,
) -> None:
    assessment = ConfidenceAssessment(
        points=[
            ConfidencePoint(kind=ConfidencePointKind.SOLID, note="knows the basics"),
        ],
        coverage_confidence=coverage_confidence,
    )

    assert assessment.coverage_confidence == coverage_confidence


@pytest.mark.parametrize("coverage_confidence", [-0.1, 1.1])
def test_confidence_assessment_rejects_out_of_range_coverage_confidence(
    coverage_confidence: float,
) -> None:
    with pytest.raises(ValidationError):
        _ = ConfidenceAssessment(
            points=[
                ConfidencePoint(
                    kind=ConfidencePointKind.SOLID, note="knows the basics"
                ),
            ],
            coverage_confidence=coverage_confidence,
        )
