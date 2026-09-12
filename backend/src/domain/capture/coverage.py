from collections.abc import Sequence

from domain.capture.value_objects import Coverage, CoverageReading, CoverageTrend

COVERAGE_FLAT_BAND = 0.05
"""How much coverage must move before the movement counts as a direction.

Without a band every reassessment registers as a trend, and `RISING` stops
meaning anything because it is almost always true. The band is what makes the
claim falsifiable, and its width is a domain decision rather than a tuning
knob: it says how much change the session considers real.
"""

COVERAGE_TREND_WINDOW = 3
"""How many of the most recent assessments a reading looks at.

The session keeps every assessment — a discarded one cannot be recovered and a
kept one can always be ignored — but a reading over the whole history would let
the opening turns outvote the present one forever. Keeping and reading are two
decisions, and this is the second.
"""

COVERAGE_HIGH = 0.7
"""Where a level stops being low. The boundary `EARLY` and `SETTLED` sit on
either side of when the trend is `FLAT`."""


def trend_of(assessments: Sequence[Coverage]) -> CoverageTrend:
    """Which way coverage has moved across the most recent assessments.

    Arithmetic, and nothing else. It reads no port, takes no session, and makes
    no claim about what the agent should say — so it is exercisable by a unit
    test with no model and no adapter in the loop, which is the whole reason it
    is placed here.

    `FLAT` for fewer than two assessments: with one value there is a level but
    no direction, and reporting a direction that cannot exist would be a lie the
    reading then repeats.
    """
    if len(assessments) < 2:
        return CoverageTrend.FLAT

    window = assessments[-COVERAGE_TREND_WINDOW:]
    if len(window) < 2:
        return CoverageTrend.FLAT

    delta = window[-1].value - window[0].value
    if abs(delta) <= COVERAGE_FLAT_BAND:
        return CoverageTrend.FLAT
    if delta > 0:
        return CoverageTrend.RISING
    return CoverageTrend.FALLING


def reading_of(assessments: Sequence[Coverage]) -> CoverageReading | None:
    """How the session is going, as one word for the instruction to speak.

    `None` when there is no assessment at all — the session has not been judged
    yet, so there is nothing to read and the `coverage_trend` block is absent.
    This is the only case in which it is absent: one assessment is enough,
    because a level alone already distinguishes `EARLY` from `SETTLED`.

    Policy, where `trend_of` is arithmetic. It combines the trend with the level
    against `COVERAGE_HIGH`, and it is the single place FR-03's judgement lives.
    Splitting the two is what lets the arithmetic be pinned by a test while the
    tone stays revisable without touching it.
    """
    if not assessments:
        return None

    trend = trend_of(assessments)
    level = assessments[-1].value

    if trend is CoverageTrend.FALLING:
        return CoverageReading.WIDENING
    if trend is CoverageTrend.RISING:
        return CoverageReading.DEEPENING
    if level >= COVERAGE_HIGH:
        return CoverageReading.SETTLED
    return CoverageReading.EARLY
