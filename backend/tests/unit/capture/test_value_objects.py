import pytest

from domain.capture.exceptions import (
    EmptyMessageContentError,
    EmptyTopicError,
    MessageContentTooLongError,
    TopicTooLongError,
)
from domain.capture.value_objects import MessageContent, Topic


def test_topic_empty_after_strip_raises_empty_topic_error() -> None:
    with pytest.raises(EmptyTopicError):
        _ = Topic(value="   ")


def test_topic_over_200_chars_raises_topic_too_long_error() -> None:
    with pytest.raises(TopicTooLongError):
        _ = Topic(value="a" * 201)


def test_message_content_empty_after_strip_raises_empty_message_content_error() -> None:
    with pytest.raises(EmptyMessageContentError):
        _ = MessageContent(value="   ")


def test_message_content_over_4000_chars_raises_message_content_too_long_error() -> (
    None
):
    with pytest.raises(MessageContentTooLongError):
        _ = MessageContent(value="a" * 4001)


def test_R2_F1_topic_stores_canonical_stripped_value() -> None:
    """R2-F1: Topic must persist strip(value), not the raw input."""
    topic = Topic(value="0\r")

    assert topic.value == "0"


def test_R2_F2_message_content_stores_canonical_stripped_value() -> None:
    """R2-F2: MessageContent must persist strip(value), not the raw input."""
    content = MessageContent(value="0\r")

    assert content.value == "0"
