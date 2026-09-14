from datetime import UTC, datetime
from typing import override

from adapters.out.in_memory.capture.tag_repository import InMemoryTagRepository
from adapters.out.in_memory.capture.topic_repository import InMemoryTopicRepository
from domain.capture.ports import EmbeddingPort
from domain.capture.topic import Topic
from domain.capture.value_objects import Embedding, Label, SimilarityScore, TopicId
from domain.capture.vocabulary import MatchCriteria, VocabularyResolver
from domain.shared.identity.model import UserId

_EMBEDDING_MODEL = "test"
_OWNER = UserId.new()


class _FixedEmbeddingPort(EmbeddingPort):
    def __init__(self, embedding: Embedding) -> None:
        self._embedding: Embedding = embedding

    @override
    async def embed(self, text: str) -> Embedding:
        _ = text
        return self._embedding


def _resolver(threshold: float = 0.85) -> VocabularyResolver:
    return VocabularyResolver(
        _FixedEmbeddingPort(
            Embedding(model=_EMBEDDING_MODEL, values=(1.0, 0.0)),
        ),
        MatchCriteria(threshold=SimilarityScore(value=threshold)),
    )


async def test_resolve_topic_reuses_an_existing_close_match() -> None:
    topics = InMemoryTopicRepository()
    resolver = _resolver()
    seeded = await resolver.resolve_topic(_OWNER, Label(value="TCP handshakes"), topics)

    resolved = await resolver.resolve_topic(
        _OWNER, Label(value="TCP handshakes"), topics
    )

    assert resolved.reused is True
    assert resolved.topic.id == seeded.topic.id


async def test_resolve_topic_mints_when_nearest_score_is_below_threshold() -> None:
    topics = InMemoryTopicRepository()
    resolver = _resolver(threshold=0.99)
    stored = Topic(
        id=TopicId.new(),
        owner_id=_OWNER,
        label=Label(value="orthogonal"),
        embedding=Embedding(model=_EMBEDDING_MODEL, values=(0.0, 1.0)),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    await topics.add(stored)

    resolved = await resolver.resolve_topic(_OWNER, Label(value="query"), topics)

    assert resolved.reused is False
    assert resolved.topic.id != stored.id


async def test_resolve_topic_mints_when_nothing_comparable_is_stored() -> None:
    topics = InMemoryTopicRepository()
    resolver = _resolver()
    other_model = Topic(
        id=TopicId.new(),
        owner_id=_OWNER,
        label=Label(value="unrelated"),
        embedding=Embedding(model="other-model", values=(1.0, 0.0)),
        created_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    await topics.add(other_model)

    resolved = await resolver.resolve_topic(_OWNER, Label(value="query"), topics)

    assert resolved.reused is False
    assert resolved.topic.id != other_model.id


async def test_resolve_tag_reuses_a_tag_minted_earlier_in_the_same_stream() -> None:
    tags = InMemoryTagRepository()
    resolver = _resolver()
    first = await resolver.resolve_tag(_OWNER, Label(value="networking"), tags)

    second = await resolver.resolve_tag(_OWNER, Label(value="networking"), tags)

    assert first.reused is False
    assert second.reused is True
    assert second.tag.id == first.tag.id
