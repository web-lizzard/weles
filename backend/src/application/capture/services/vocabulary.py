from collections.abc import Sequence

from application.capture.ports import EmbeddingPort
from application.capture.value_objects import ResolvedTag, ResolvedTopic
from domain.capture.ports import TagRepository, TopicRepository
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import Embedding, Label
from domain.capture.vocabulary import MatchCriteria, VocabularyMatch


class VocabularyResolver:
    def __init__(self, embedding: EmbeddingPort, criteria: MatchCriteria) -> None:
        self._embedding: EmbeddingPort = embedding
        self._criteria: MatchCriteria = criteria

    async def resolve_topic(
        self, label: Label, topics: TopicRepository
    ) -> ResolvedTopic:
        embedding, match = await self._best_match(label, await topics.candidates())
        if match is not None:
            return ResolvedTopic(topic=match.entry, reused=True)
        topic = Topic.mint(label, embedding)
        await topics.add(topic)
        return ResolvedTopic(topic=topic, reused=False)

    async def resolve_tag(self, label: Label, tags: TagRepository) -> ResolvedTag:
        embedding, match = await self._best_match(label, await tags.candidates())
        if match is not None:
            return ResolvedTag(tag=match.entry, reused=True)
        tag = Tag.mint(label, embedding)
        await tags.add(tag)
        return ResolvedTag(tag=tag, reused=False)

    async def _best_match[VocabularyEntryT: (Topic, Tag)](
        self, label: Label, candidates: Sequence[VocabularyEntryT]
    ) -> tuple[Embedding, VocabularyMatch[VocabularyEntryT] | None]:
        embedding = await self._embedding.embed(label.value)
        return embedding, self._criteria.best_match(embedding, candidates)
