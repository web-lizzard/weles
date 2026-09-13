from math import sqrt

from domain.capture.exceptions import (
    EmbeddingDimensionMismatchError,
    ZeroMagnitudeEmbeddingError,
)
from domain.capture.value_objects import (
    SIMILARITY_SCORE_MAX,
    SIMILARITY_SCORE_MIN,
    Embedding,
    SimilarityScore,
)


def cosine_similarity(left: Embedding, right: Embedding) -> SimilarityScore:
    if len(left.values) != len(right.values):
        raise EmbeddingDimensionMismatchError
    if left.values == right.values:
        _ = _scaled_to_largest_component(left.values)
        return SimilarityScore(value=SIMILARITY_SCORE_MAX)
    left_scaled = _scaled_to_largest_component(left.values)
    right_scaled = _scaled_to_largest_component(right.values)
    dot = sum(a * b for a, b in zip(left_scaled, right_scaled, strict=True))
    magnitudes = _magnitude(left_scaled) * _magnitude(right_scaled)
    return SimilarityScore(value=_clamped_to_score_range(dot / magnitudes))


def _scaled_to_largest_component(values: tuple[float, ...]) -> tuple[float, ...]:
    largest = max(abs(value) for value in values)
    if largest == 0.0:
        raise ZeroMagnitudeEmbeddingError
    return tuple(value / largest for value in values)


def _magnitude(values: tuple[float, ...]) -> float:
    return sqrt(sum(value * value for value in values))


def _clamped_to_score_range(value: float) -> float:
    return min(max(value, SIMILARITY_SCORE_MIN), SIMILARITY_SCORE_MAX)
