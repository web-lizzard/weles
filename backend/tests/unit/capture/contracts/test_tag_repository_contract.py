from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast

import pytest

from adapters.out.in_memory.capture.tag_repository import InMemoryTagRepository
from domain.capture.ports import TagRepository
from domain.capture.tag import Tag
from domain.capture.value_objects import Embedding, Label, TagId

_IMPLEMENTATIONS: list[Callable[[], TagRepository]] = [
    cast(Callable[[], TagRepository], InMemoryTagRepository),
]


def _sample_tag() -> Tag:
    return Tag(
        id=TagId.new(),
        label=Label(value="networking"),
        embedding=Embedding(values=(0.3, 0.4)),
        created_at=datetime.now(UTC),
    )


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_add_then_get_returns_the_saved_tag(
    make_repository: Callable[[], TagRepository],
) -> None:
    repository = make_repository()
    tag = _sample_tag()

    await repository.add(tag)
    result = await repository.get(tag.id)

    assert result == tag


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_get_returns_none_for_unknown_tag_id(
    make_repository: Callable[[], TagRepository],
) -> None:
    repository = make_repository()

    result = await repository.get(TagId.new())

    assert result is None


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_second_add_with_same_id_overwrites(
    make_repository: Callable[[], TagRepository],
) -> None:
    repository = make_repository()
    original = _sample_tag()
    updated = original.model_copy(update={"label": Label(value="protocols")})

    await repository.add(original)
    await repository.add(updated)
    result = await repository.get(original.id)

    assert result == updated
