from application.capture.ports import EmbeddingPort
from domain.capture.ports import TagRepository, TopicRepository
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import Label


class VocabularyResolver:
    def __init__(self, embedding: EmbeddingPort) -> None:
        self._embedding: EmbeddingPort = embedding

    async def resolve_topic(self, label: Label, topics: TopicRepository) -> Topic:
        embedding = await self._embedding.embed(label.value)
        topic = Topic.mint(label, embedding)
        await topics.add(topic)
        return topic

    async def resolve_tag(self, label: Label, tags: TagRepository) -> Tag:
        embedding = await self._embedding.embed(label.value)
        tag = Tag.mint(label, embedding)
        await tags.add(tag)
        return tag
