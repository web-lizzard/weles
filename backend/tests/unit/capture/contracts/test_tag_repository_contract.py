from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast

import pytest

from adapters.out.in_memory.capture.tag_repository import InMemoryTagRepository
from domain.capture.ports import TagRepository
from domain.capture.tag import Tag
from domain.capture.value_objects import Embedding, Label, TagId

_EMBEDDING_MODEL = "test"
_OTHER_MODEL = "other-model"

_IMPLEMENTATIONS: list[Callable[[], TagRepository]] = [
    cast(Callable[[], TagRepository], InMemoryTagRepository),
]


def _sample_tag() -> Tag:
    return Tag(
        id=TagId.new(),
        label=Label(value="networking"),
        embedding=Embedding(model=_EMBEDDING_MODEL, values=(0.3, 0.4)),
        created_at=datetime.now(UTC),
    )


def _tag_with(
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


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_nearest_returns_none_for_empty_store(
    make_repository: Callable[[], TagRepository],
) -> None:
    repository = make_repository()
    query = Embedding(model=_EMBEDDING_MODEL, values=(1.0, 0.0))

    result = await repository.nearest(query)

    assert result is None


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_nearest_returns_highest_scoring_entry_with_its_score(
    make_repository: Callable[[], TagRepository],
) -> None:
    repository = make_repository()
    query = Embedding(model=_EMBEDDING_MODEL, values=(1.0, 0.0))
    weaker = _tag_with(
        Embedding(model=_EMBEDDING_MODEL, values=(0.7, 0.7)),
        datetime(2026, 1, 1, tzinfo=UTC),
        label="weaker",
    )
    stronger = _tag_with(
        Embedding(model=_EMBEDDING_MODEL, values=(1.0, 0.0)),
        datetime(2026, 1, 2, tzinfo=UTC),
        label="stronger",
    )

    await repository.add(weaker)
    await repository.add(stronger)
    match = await repository.nearest(query)

    assert match is not None
    assert match.entry is stronger
    assert match.score.value == pytest.approx(1.0)


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_nearest_breaks_equal_scores_by_earlier_created_at(
    make_repository: Callable[[], TagRepository],
) -> None:
    repository = make_repository()
    query = Embedding(model=_EMBEDDING_MODEL, values=(1.0, 0.0))
    older = _tag_with(
        Embedding(model=_EMBEDDING_MODEL, values=(1.0, 0.0)),
        datetime(2026, 1, 1, tzinfo=UTC),
        label="older",
    )
    newer = _tag_with(
        Embedding(model=_EMBEDDING_MODEL, values=(1.0, 0.0)),
        datetime(2026, 1, 2, tzinfo=UTC),
        label="newer",
    )

    await repository.add(newer)
    await repository.add(older)
    match = await repository.nearest(query)

    assert match is not None
    assert match.entry is older


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_nearest_ignores_other_model_and_dimension(
    make_repository: Callable[[], TagRepository],
) -> None:
    repository = make_repository()
    query = Embedding(model=_EMBEDDING_MODEL, values=(1.0, 0.0))
    other_model = _tag_with(
        Embedding(model=_OTHER_MODEL, values=(1.0, 0.0)),
        datetime(2026, 1, 1, tzinfo=UTC),
        label="other-model",
    )
    other_dimension = _tag_with(
        Embedding(model=_EMBEDDING_MODEL, values=(1.0,)),
        datetime(2026, 1, 2, tzinfo=UTC),
        label="other-dimension",
    )

    await repository.add(other_model)
    await repository.add(other_dimension)
    match = await repository.nearest(query)

    assert match is None
