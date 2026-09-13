import struct
from math import inf, nan

import pytest

from domain.capture.exceptions import (
    CoverageOutOfRangeError,
    EmbeddingComponentOutOfRangeError,
    EmptyEmbeddingError,
    EmptyEmbeddingModelError,
    EmptyLabelError,
    EmptyMessageContentError,
    EmptySessionTopicError,
    MessageContentTooLongError,
    SessionTopicTooLongError,
    ZeroMagnitudeEmbeddingError,
)
from domain.capture.value_objects import (
    COVERAGE_MAX,
    COVERAGE_MIN,
    Coverage,
    Embedding,
    Label,
    MessageContent,
    SessionTopic,
)

_EMBEDDING_MODEL = "test"


def test_session_topic_empty_after_strip_raises_empty_session_topic_error() -> None:
    with pytest.raises(EmptySessionTopicError):
        _ = SessionTopic(value="   ")


def test_session_topic_over_200_chars_raises_session_topic_too_long_error() -> None:
    with pytest.raises(SessionTopicTooLongError):
        _ = SessionTopic(value="a" * 201)


def test_message_content_empty_after_strip_raises_empty_message_content_error() -> None:
    with pytest.raises(EmptyMessageContentError):
        _ = MessageContent(value="   ")


def test_message_content_over_4000_chars_raises_message_content_too_long_error() -> (
    None
):
    with pytest.raises(MessageContentTooLongError):
        _ = MessageContent(value="a" * 4001)


def test_R2_F1_session_topic_stores_canonical_stripped_value() -> None:
    """R2-F1: SessionTopic must persist strip(value), not the raw input."""
    topic = SessionTopic(value="0\r")

    assert topic.value == "0"


def test_R2_F2_message_content_stores_canonical_stripped_value() -> None:
    """R2-F2: MessageContent must persist strip(value), not the raw input."""
    content = MessageContent(value="0\r")

    assert content.value == "0"


def test_label_empty_after_strip_raises_empty_label_error() -> None:
    with pytest.raises(EmptyLabelError):
        _ = Label(value="   ")


def test_embedding_empty_values_raises_empty_embedding_error() -> None:
    with pytest.raises(EmptyEmbeddingError):
        _ = Embedding(model=_EMBEDDING_MODEL, values=())


def _float32_components(values: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(struct.unpack("f", struct.pack("f", value))[0] for value in values)


def test_embedding_components_equal_their_float32_values_after_construction() -> None:
    raw = (1.0000000001, -2.0000000002)
    embedding = Embedding(model=_EMBEDDING_MODEL, values=raw)
    rebuilt = Embedding(model=_EMBEDDING_MODEL, values=_float32_components(raw))

    assert embedding == rebuilt
    assert embedding.values == _float32_components(raw)


@pytest.mark.parametrize(
    "value",
    [float("inf"), float("nan"), 3.5e38],
)
def test_embedding_rejects_out_of_range_or_non_finite_components(value: float) -> None:
    with pytest.raises(EmbeddingComponentOutOfRangeError):
        _ = Embedding(model=_EMBEDDING_MODEL, values=(value,))


def test_embedding_rejects_all_zero_components() -> None:
    with pytest.raises(ZeroMagnitudeEmbeddingError):
        _ = Embedding(model=_EMBEDDING_MODEL, values=(0.0, 0.0))


@pytest.mark.parametrize("model", ["", "   "])
def test_embedding_rejects_blank_model(model: str) -> None:
    with pytest.raises(EmptyEmbeddingModelError):
        _ = Embedding(model=model, values=(1.0,))


def test_coverage_accepts_closed_unit_interval() -> None:
    low = Coverage(value=COVERAGE_MIN)
    high = Coverage(value=COVERAGE_MAX)

    assert low.value == COVERAGE_MIN
    assert high.value == COVERAGE_MAX


@pytest.mark.parametrize(
    "value",
    [
        -0.01,
        1.01,
        nan,
        inf,
        -inf,
    ],
)
def test_coverage_raises_out_of_range_for_invalid_values(value: float) -> None:
    with pytest.raises(CoverageOutOfRangeError):
        _ = Coverage(value=value)
