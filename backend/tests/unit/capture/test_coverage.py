# pyright: reportPrivateUsage=false

import pytest

from domain.capture.coverage import (
    COVERAGE_FLAT_BAND,
    COVERAGE_HIGH,
    COVERAGE_TREND_WINDOW,
    reading_of,
    trend_of,
)
from domain.capture.instructions import _COVERAGE_READING_PROSE
from domain.capture.value_objects import Coverage, CoverageReading, CoverageTrend


def _assessments(*values: float) -> tuple[Coverage, ...]:
    return tuple(Coverage(value=value) for value in values)


def test_trend_of_is_flat_with_no_assessments() -> None:
    assert trend_of(()) is CoverageTrend.FLAT


def test_trend_of_is_flat_with_one_assessment() -> None:
    assert trend_of(_assessments(0.4)) is CoverageTrend.FLAT


def test_trend_of_is_flat_when_movement_stays_within_flat_band() -> None:
    start = 0.5
    end = start + COVERAGE_FLAT_BAND - 0.01

    assert trend_of(_assessments(start, end)) is CoverageTrend.FLAT


def test_trend_of_is_rising_when_movement_exceeds_flat_band() -> None:
    start = 0.4
    end = start + COVERAGE_FLAT_BAND + 0.01

    assert trend_of(_assessments(start, end)) is CoverageTrend.RISING


def test_trend_of_is_falling_when_movement_exceeds_flat_band_downward() -> None:
    start = 0.8
    end = start - COVERAGE_FLAT_BAND - 0.01

    assert trend_of(_assessments(start, end)) is CoverageTrend.FALLING


def test_trend_of_ignores_assessments_outside_trend_window() -> None:
    """Only the last COVERAGE_TREND_WINDOW entries decide the direction."""
    stale_high = 1.0
    recent = (0.1, 0.2, 0.5)
    history = _assessments(stale_high, *recent)

    assert len(history) == COVERAGE_TREND_WINDOW + 1
    assert trend_of(history) is CoverageTrend.RISING
    assert trend_of(_assessments(stale_high, 0.05)) is CoverageTrend.FALLING


def test_reading_of_is_none_for_empty_history() -> None:
    assert reading_of(()) is None


def test_reading_of_is_early_for_a_single_low_assessment() -> None:
    assert reading_of(_assessments(0.3)) is CoverageReading.EARLY


def test_reading_of_is_settled_for_a_single_high_assessment() -> None:
    assert reading_of(_assessments(COVERAGE_HIGH)) is CoverageReading.SETTLED


def test_reading_of_is_deepening_on_a_rising_trend() -> None:
    assert reading_of(_assessments(0.3, 0.5)) is CoverageReading.DEEPENING


def test_reading_of_is_widening_on_a_falling_trend() -> None:
    assert reading_of(_assessments(0.8, 0.6)) is CoverageReading.WIDENING


def test_reading_of_is_early_on_flat_trend_below_high() -> None:
    assert reading_of(_assessments(0.4, 0.42)) is CoverageReading.EARLY


def test_reading_of_is_settled_on_flat_trend_at_or_above_high() -> None:
    assert reading_of(_assessments(0.75, 0.76)) is CoverageReading.SETTLED


@pytest.mark.parametrize("reading", list(CoverageReading))
def test_every_coverage_reading_has_prose(reading: CoverageReading) -> None:
    assert reading in _COVERAGE_READING_PROSE
    assert _COVERAGE_READING_PROSE[reading]
