import pytest

from application.capture.exceptions import EmptyConfidencePointError
from application.capture.value_objects import ConfidencePoint, ConfidencePointKind


def test_confidence_point_empty_note_raises_empty_confidence_point_error() -> None:
    with pytest.raises(EmptyConfidencePointError):
        _ = ConfidencePoint(kind=ConfidencePointKind.SOLID, note="   ")
