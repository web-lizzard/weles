from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.in_memory.capture.topic_repository import InMemoryTopicRepository
from adapters.out.sqlalchemy.capture.topic_repository import SqlAlchemyTopicRepository
from adapters.out.sqlalchemy.engine import create_session_factory
from domain.capture.ports import TopicRepository
from domain.capture.topic import Topic
from domain.capture.value_objects import Embedding, Label, TopicId
from domain.shared.identity.model import UserId

_EMBEDDING_MODEL = "test"
_OTHER_MODEL = "other-model"
_OWNER = UserId.new()


class _CommittingTopicRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def add(self, topic: Topic) -> None:
        async with self._session_factory() as db_session:
            await SqlAlchemyTopicRepository(db_session).add(topic)
            await db_session.commit()

    async def get(self, topic_id: TopicId) -> Topic | None:
        async with self._session_factory() as db_session:
            return await SqlAlchemyTopicRepository(db_session).get(topic_id)

    async def nearest(self, owner: UserId, embedding: Embedding):
        async with self._session_factory() as db_session:
            return await SqlAlchemyTopicRepository(db_session).nearest(owner, embedding)


@pytest.fixture(
    params=["in_memory", pytest.param("postgres", marks=pytest.mark.postgres)]
)
def repository(request: pytest.FixtureRequest) -> TopicRepository:
    if request.param == "in_memory":  # pyright: ignore[reportAny]
        return InMemoryTopicRepository()
    engine: AsyncEngine = request.getfixturevalue("engine")  # pyright: ignore[reportAny]
    session_factory = create_session_factory(engine)
    return _CommittingTopicRepository(session_factory)


def _sample_topic() -> Topic:
    return Topic(
        id=TopicId.new(),
        owner_id=_OWNER,
        label=Label(value="TCP handshakes"),
        embedding=Embedding(model=_EMBEDDING_MODEL, values=(0.1, 0.2)),
        created_at=datetime.now(UTC),
    )


def _topic_with(
    embedding: Embedding,
    created_at: datetime,
    *,
    label: str = "topic",
    owner: UserId = _OWNER,
) -> Topic:
    return Topic(
        id=TopicId.new(),
        owner_id=owner,
        label=Label(value=label),
        embedding=embedding,
        created_at=created_at,
    )


async def test_add_then_get_returns_the_saved_topic(
    repository: TopicRepository,
) -> None:
    topic = _sample_topic()

    await repository.add(topic)
    result = await repository.get(topic.id)

    assert result == topic


async def test_get_returns_none_for_unknown_topic_id(
    repository: TopicRepository,
) -> None:
    result = await repository.get(TopicId.new())

    assert result is None


async def test_second_add_with_same_id_overwrites(
    repository: TopicRepository,
) -> None:
    original = _sample_topic()
    updated = original.model_copy(
        update={"label": Label(value="Connection establishment")}
    )

    await repository.add(original)
    await repository.add(updated)
    result = await repository.get(original.id)

    assert result == updated


async def test_nearest_returns_none_for_empty_store(
    repository: TopicRepository,
) -> None:
    query = Embedding(model=_EMBEDDING_MODEL, values=(1.0, 0.0))

    result = await repository.nearest(_OWNER, query)

    assert result is None


async def test_nearest_returns_highest_scoring_entry_with_its_score(
    repository: TopicRepository,
) -> None:
    query = Embedding(model=_EMBEDDING_MODEL, values=(1.0, 0.0))
    weaker = _topic_with(
        Embedding(model=_EMBEDDING_MODEL, values=(0.7, 0.7)),
        datetime(2026, 1, 1, tzinfo=UTC),
        label="weaker",
    )
    stronger = _topic_with(
        Embedding(model=_EMBEDDING_MODEL, values=(1.0, 0.0)),
        datetime(2026, 1, 2, tzinfo=UTC),
        label="stronger",
    )

    await repository.add(weaker)
    await repository.add(stronger)
    match = await repository.nearest(_OWNER, query)

    assert match is not None
    assert match.entry == stronger
    assert match.score.value == pytest.approx(1.0)


async def test_nearest_breaks_equal_scores_by_earlier_created_at(
    repository: TopicRepository,
) -> None:
    query = Embedding(model=_EMBEDDING_MODEL, values=(1.0, 0.0))
    older = _topic_with(
        Embedding(model=_EMBEDDING_MODEL, values=(1.0, 0.0)),
        datetime(2026, 1, 1, tzinfo=UTC),
        label="older",
    )
    newer = _topic_with(
        Embedding(model=_EMBEDDING_MODEL, values=(1.0, 0.0)),
        datetime(2026, 1, 2, tzinfo=UTC),
        label="newer",
    )

    await repository.add(newer)
    await repository.add(older)
    match = await repository.nearest(_OWNER, query)

    assert match is not None
    assert match.entry == older


async def test_nearest_ignores_other_model_and_dimension(
    repository: TopicRepository,
) -> None:
    query = Embedding(model=_EMBEDDING_MODEL, values=(1.0, 0.0))
    other_model = _topic_with(
        Embedding(model=_OTHER_MODEL, values=(1.0, 0.0)),
        datetime(2026, 1, 1, tzinfo=UTC),
        label="other-model",
    )
    other_dimension = _topic_with(
        Embedding(model=_EMBEDDING_MODEL, values=(1.0,)),
        datetime(2026, 1, 2, tzinfo=UTC),
        label="other-dimension",
    )

    await repository.add(other_model)
    await repository.add(other_dimension)
    match = await repository.nearest(_OWNER, query)

    assert match is None
