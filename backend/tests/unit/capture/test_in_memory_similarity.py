import pytest

from adapters.out.in_memory.capture.similarity import cosine_similarity
from domain.capture.exceptions import (
    EmbeddingDimensionMismatchError,
    ZeroMagnitudeEmbeddingError,
)
from domain.capture.value_objects import Embedding

_EMBEDDING_MODEL = "test"


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
    score = cosine_similarity(
        Embedding(model=_EMBEDDING_MODEL, values=left),
        Embedding(model=_EMBEDDING_MODEL, values=right),
    )

    assert score.value == pytest.approx(expected)


def test_cosine_similarity_survives_extreme_component_magnitudes() -> None:
    left = Embedding(model=_EMBEDDING_MODEL, values=(3.0e38, 3.0e38))
    right = Embedding(model=_EMBEDDING_MODEL, values=(3.0e38, -3.0e38))

    score = cosine_similarity(left, right)

    assert score.value == pytest.approx(0.0)


def test_cosine_similarity_raises_on_dimension_mismatch() -> None:
    left = Embedding(model=_EMBEDDING_MODEL, values=(1.0, 2.0))
    right = Embedding(model=_EMBEDDING_MODEL, values=(1.0,))

    with pytest.raises(EmbeddingDimensionMismatchError):
        _ = cosine_similarity(left, right)


def test_cosine_similarity_raises_on_zero_magnitude() -> None:
    with pytest.raises(ZeroMagnitudeEmbeddingError):
        _ = Embedding(model=_EMBEDDING_MODEL, values=(0.0, 0.0))
