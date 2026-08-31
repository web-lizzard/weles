from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast

import pytest

from adapters.out.in_memory.capture.topic_repository import InMemoryTopicRepository
from domain.capture.ports import TopicRepository
from domain.capture.topic import Topic
from domain.capture.value_objects import Embedding, Label, TopicId

_IMPLEMENTATIONS: list[Callable[[], TopicRepository]] = [
    cast(Callable[[], TopicRepository], InMemoryTopicRepository),
]


def _sample_topic() -> Topic:
    return Topic(
        id=TopicId.new(),
        label=Label(value="TCP handshakes"),
        embedding=Embedding(values=(0.1, 0.2)),
        created_at=datetime.now(UTC),
    )


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_add_then_get_returns_the_saved_topic(
    make_repository: Callable[[], TopicRepository],
) -> None:
    repository = make_repository()
    topic = _sample_topic()

    await repository.add(topic)
    result = await repository.get(topic.id)

    assert result == topic


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_get_returns_none_for_unknown_topic_id(
    make_repository: Callable[[], TopicRepository],
) -> None:
    repository = make_repository()

    result = await repository.get(TopicId.new())

    assert result is None


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_second_add_with_same_id_overwrites(
    make_repository: Callable[[], TopicRepository],
) -> None:
    repository = make_repository()
    original = _sample_topic()
    updated = original.model_copy(
        update={"label": Label(value="Connection establishment")}
    )

    await repository.add(original)
    await repository.add(updated)
    result = await repository.get(original.id)

    assert result == updated
