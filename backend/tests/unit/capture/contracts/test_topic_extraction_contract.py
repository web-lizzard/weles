from collections.abc import Callable

import pytest

from adapters.out.in_memory.capture.topic_extraction import (
    DeterministicTopicExtractionAdapter,
)
from application.capture.ports import TopicExtractionPort
from domain.capture.value_objects import MessageContent

_IMPLEMENTATIONS: list[Callable[[], TopicExtractionPort]] = [
    DeterministicTopicExtractionAdapter,
]


@pytest.mark.parametrize("make_adapter", _IMPLEMENTATIONS, ids=["deterministic"])
async def test_extract_returns_a_valid_nonempty_topic(
    make_adapter: Callable[[], TopicExtractionPort],
) -> None:
    adapter = make_adapter()
    content = MessageContent(
        value="Let's talk through how TCP handshakes establish a connection"
    )

    topic = await adapter.extract(content)

    assert topic.value.strip() != ""
