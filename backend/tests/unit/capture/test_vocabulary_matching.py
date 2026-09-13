import pytest

from domain.capture.exceptions import SimilarityScoreOutOfRangeError
from domain.capture.value_objects import SimilarityScore
from domain.capture.vocabulary import MatchCriteria


@pytest.mark.parametrize(
    "value",
    [1.1, float("inf"), float("nan")],
)
def test_similarity_score_rejects_out_of_range_and_non_finite(value: float) -> None:
    with pytest.raises(SimilarityScoreOutOfRangeError):
        _ = SimilarityScore(value=value)


def test_match_criteria_accepts_score_equal_to_threshold() -> None:
    threshold = SimilarityScore(value=0.85)
    criteria = MatchCriteria(threshold=threshold)

    assert criteria.accepts(threshold) is True


def test_match_criteria_rejects_score_just_below_threshold() -> None:
    criteria = MatchCriteria(threshold=SimilarityScore(value=0.85))

    assert criteria.accepts(SimilarityScore(value=0.849999)) is False
