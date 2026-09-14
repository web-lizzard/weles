from pydantic import BaseModel

from domain.capture.ports import EmbeddingPort, TagRepository, TopicRepository
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import Label, SimilarityScore
from domain.shared.identity.model import UserId


class MatchCriteria(BaseModel, frozen=True):
    threshold: SimilarityScore

    def accepts(self, score: SimilarityScore) -> bool:
        return score.value >= self.threshold.value


class ResolvedTopic(BaseModel, frozen=True):
    topic: Topic
    reused: bool


class ResolvedTag(BaseModel, frozen=True):
    tag: Tag
    reused: bool


class VocabularyResolver:
    def __init__(self, embedding: EmbeddingPort, criteria: MatchCriteria) -> None:
        self._embedding: EmbeddingPort = embedding
        self._criteria: MatchCriteria = criteria

    async def resolve_topic(
        self, owner: UserId, label: Label, topics: TopicRepository
    ) -> ResolvedTopic:
        embedding = await self._embedding.embed(label.value)
        match = await topics.nearest(owner, embedding)
        if match is not None and self._criteria.accepts(match.score):
            return ResolvedTopic(topic=match.entry, reused=True)
        topic = Topic.mint(owner, label, embedding)
        await topics.add(topic)
        return ResolvedTopic(topic=topic, reused=False)

    async def resolve_tag(
        self, owner: UserId, label: Label, tags: TagRepository
    ) -> ResolvedTag:
        embedding = await self._embedding.embed(label.value)
        match = await tags.nearest(owner, embedding)
        if match is not None and self._criteria.accepts(match.score):
            return ResolvedTag(tag=match.entry, reused=True)
        tag = Tag.mint(owner, label, embedding)
        await tags.add(tag)
        return ResolvedTag(tag=tag, reused=False)
