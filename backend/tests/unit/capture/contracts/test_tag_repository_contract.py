from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.in_memory.capture.tag_repository import InMemoryTagRepository
from adapters.out.sqlalchemy.capture.tag_repository import SqlAlchemyTagRepository
from adapters.out.sqlalchemy.engine import create_session_factory
from domain.capture.ports import TagRepository
from domain.capture.tag import Tag
from domain.capture.value_objects import Embedding, Label, TagId

_EMBEDDING_MODEL = "test"
_OTHER_MODEL = "other-model"


class _CommittingTagRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def add(self, tag: Tag) -> None:
        async with self._session_factory() as db_session:
            await SqlAlchemyTagRepository(db_session).add(tag)
            await db_session.commit()

    async def get(self, tag_id: TagId) -> Tag | None:
        async with self._session_factory() as db_session:
            return await SqlAlchemyTagRepository(db_session).get(tag_id)

    async def nearest(self, embedding: Embedding):
        async with self._session_factory() as db_session:
            return await SqlAlchemyTagRepository(db_session).nearest(embedding)


@pytest.fixture(
    params=["in_memory", pytest.param("postgres", marks=pytest.mark.postgres)]
)
def repository(request: pytest.FixtureRequest) -> TagRepository:
    if request.param == "in_memory":  # pyright: ignore[reportAny]
        return InMemoryTagRepository()
    engine: AsyncEngine = request.getfixturevalue("engine")  # pyright: ignore[reportAny]
    session_factory = create_session_factory(engine)
    return _CommittingTagRepository(session_factory)


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


async def test_add_then_get_returns_the_saved_tag(repository: TagRepository) -> None:
    tag = _sample_tag()

    await repository.add(tag)
    result = await repository.get(tag.id)

    assert result == tag


async def test_get_returns_none_for_unknown_tag_id(repository: TagRepository) -> None:
    result = await repository.get(TagId.new())

    assert result is None


async def test_second_add_with_same_id_overwrites(repository: TagRepository) -> None:
    original = _sample_tag()
    updated = original.model_copy(update={"label": Label(value="protocols")})

    await repository.add(original)
    await repository.add(updated)
    result = await repository.get(original.id)

    assert result == updated


async def test_nearest_returns_none_for_empty_store(repository: TagRepository) -> None:
    query = Embedding(model=_EMBEDDING_MODEL, values=(1.0, 0.0))

    result = await repository.nearest(query)

    assert result is None


async def test_nearest_returns_highest_scoring_entry_with_its_score(
    repository: TagRepository,
) -> None:
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


async def test_nearest_breaks_equal_scores_by_earlier_created_at(
    repository: TagRepository,
) -> None:
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


async def test_nearest_ignores_other_model_and_dimension(
    repository: TagRepository,
) -> None:
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
