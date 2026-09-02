from adapters.out.in_memory.capture.embedding import DeterministicEmbeddingAdapter
from adapters.out.in_memory.capture.tag_repository import InMemoryTagRepository
from adapters.out.in_memory.capture.topic_repository import InMemoryTopicRepository
from application.capture.services.vocabulary import VocabularyResolver
from domain.capture.value_objects import Label, SimilarityScore
from domain.capture.vocabulary import MatchCriteria


def _resolver() -> VocabularyResolver:
    return VocabularyResolver(
        DeterministicEmbeddingAdapter(),
        MatchCriteria(threshold=SimilarityScore(value=0.85)),
    )


async def test_resolve_topic_reuses_an_existing_close_match() -> None:
    topics = InMemoryTopicRepository()
    resolver = _resolver()
    seeded = await resolver.resolve_topic(Label(value="TCP handshakes"), topics)

    resolved = await resolver.resolve_topic(Label(value="TCP handshakes"), topics)

    assert resolved.reused is True
    assert resolved.topic.id == seeded.topic.id
    assert len(await topics.candidates()) == 1


async def test_resolve_topic_mints_when_nothing_clears_the_threshold() -> None:
    topics = InMemoryTopicRepository()
    resolver = _resolver()
    seeded = await resolver.resolve_topic(Label(value="TCP handshakes"), topics)

    resolved = await resolver.resolve_topic(Label(value="grocery list"), topics)

    assert resolved.reused is False
    assert resolved.topic.id != seeded.topic.id
    assert len(await topics.candidates()) == 2


async def test_resolve_tag_reuses_a_tag_minted_earlier_in_the_same_stream() -> None:
    tags = InMemoryTagRepository()
    resolver = _resolver()
    first = await resolver.resolve_tag(Label(value="networking"), tags)

    second = await resolver.resolve_tag(Label(value="networking"), tags)

    assert first.reused is False
    assert second.reused is True
    assert second.tag.id == first.tag.id
    assert len(await tags.candidates()) == 1
