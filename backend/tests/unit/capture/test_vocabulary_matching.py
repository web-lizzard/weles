from datetime import UTC, datetime

import pytest

from domain.capture.exceptions import (
    EmbeddingDimensionMismatchError,
    SimilarityScoreOutOfRangeError,
    ZeroMagnitudeEmbeddingError,
)
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import (
    Embedding,
    Label,
    SimilarityScore,
    TagId,
    TopicId,
)
from domain.capture.vocabulary import MatchCriteria, VocabularyMatch


def _topic(
    embedding: Embedding,
    created_at: datetime,
    *,
    label: str = "topic",
) -> Topic:
    return Topic(
        id=TopicId.new(),
        label=Label(value=label),
        embedding=embedding,
        created_at=created_at,
    )


def _tag(
    embedding: Embedding,
    created_at: datetime,
    *,
    label: str = "tag",
) -> Tag:
    return Tag(
        id=TagId.new(),
        label=Label(value=label),
        embedding=embedding,
        created_at=created_at,
    )


@pytest.mark.parametrize(
    "value",
    [1.1, float("inf"), float("nan")],
)
def test_similarity_score_rejects_out_of_range_and_non_finite(value: float) -> None:
    with pytest.raises(SimilarityScoreOutOfRangeError):
        _ = SimilarityScore(value=value)


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        ((1.0, 0.0), (1.0, 0.0), 1.0),
        ((1.0, 0.0), (0.0, 1.0), 0.0),
        ((1.0, 0.0), (-1.0, 0.0), -1.0),
    ],
)
def test_cosine_similarity_for_unit_direction_pairs(
    left: tuple[float, ...],
    right: tuple[float, ...],
    expected: float,
) -> None:
    score = Embedding(values=left).cosine_similarity(Embedding(values=right))

    assert score.value == pytest.approx(expected)


def test_cosine_similarity_survives_extreme_component_magnitudes() -> None:
    left = Embedding(values=(1e200, 1e200))
    right = Embedding(values=(1e200, -1e200))

    score = left.cosine_similarity(right)

    assert score.value == pytest.approx(0.0)


def test_cosine_similarity_raises_on_dimension_mismatch() -> None:
    left = Embedding(values=(1.0, 2.0))
    right = Embedding(values=(1.0,))

    with pytest.raises(EmbeddingDimensionMismatchError):
        _ = left.cosine_similarity(right)


def test_cosine_similarity_raises_on_zero_magnitude() -> None:
    left = Embedding(values=(0.0, 0.0))
    right = Embedding(values=(1.0, 0.0))

    with pytest.raises(ZeroMagnitudeEmbeddingError):
        _ = left.cosine_similarity(right)


def test_best_match_returns_none_for_empty_candidates() -> None:
    criteria = MatchCriteria(threshold=SimilarityScore(value=0.85))
    target = Embedding(values=(1.0, 0.0))

    assert criteria.best_match(target, []) is None


def test_best_match_returns_none_when_every_candidate_is_below_threshold() -> None:
    criteria = MatchCriteria(threshold=SimilarityScore(value=0.85))
    target = Embedding(values=(1.0, 0.0))
    orthogonal = _topic(Embedding(values=(0.0, 1.0)), datetime(2026, 1, 1, tzinfo=UTC))

    assert criteria.best_match(target, [orthogonal]) is None


def test_best_match_returns_highest_scoring_candidate_above_threshold() -> None:
    criteria = MatchCriteria(threshold=SimilarityScore(value=0.5))
    target = Embedding(values=(1.0, 0.0))
    weaker = _topic(
        Embedding(values=(0.7, 0.7)),
        datetime(2026, 1, 1, tzinfo=UTC),
        label="weaker",
    )
    stronger = _topic(
        Embedding(values=(1.0, 0.0)),
        datetime(2026, 1, 2, tzinfo=UTC),
        label="stronger",
    )

    match = criteria.best_match(target, [weaker, stronger])

    assert isinstance(match, VocabularyMatch)
    assert match.entry is stronger
    assert match.score.value == pytest.approx(1.0)


def test_best_match_breaks_score_ties_by_earlier_created_at() -> None:
    criteria = MatchCriteria(threshold=SimilarityScore(value=0.5))
    target = Embedding(values=(1.0, 0.0))
    older = _tag(
        Embedding(values=(1.0, 0.0)),
        datetime(2026, 1, 1, tzinfo=UTC),
        label="older",
    )
    newer = _tag(
        Embedding(values=(1.0, 0.0)),
        datetime(2026, 1, 2, tzinfo=UTC),
        label="newer",
    )

    match = criteria.best_match(target, [newer, older])

    assert match is not None
    assert match.entry is older
