from application.capture.ports import EmbeddingPort
from application.capture.value_objects import ResolvedTag, ResolvedTopic
from domain.capture.ports import TagRepository, TopicRepository
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import Label
from domain.capture.vocabulary import MatchCriteria


class VocabularyResolver:
    def __init__(self, embedding: EmbeddingPort, criteria: MatchCriteria) -> None:
        self._embedding: EmbeddingPort = embedding
        self._criteria: MatchCriteria = criteria

    async def resolve_topic(
        self, label: Label, topics: TopicRepository
    ) -> ResolvedTopic:
        embedding = await self._embedding.embed(label.value)
        topic = Topic.mint(label, embedding)
        await topics.add(topic)
        return ResolvedTopic(topic=topic, reused=False)

    async def resolve_tag(self, label: Label, tags: TagRepository) -> ResolvedTag:
        embedding = await self._embedding.embed(label.value)
        tag = Tag.mint(label, embedding)
        await tags.add(tag)
        return ResolvedTag(tag=tag, reused=False)
