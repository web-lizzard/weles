from application.capture.ports import EmbeddingPort
from domain.capture.ports import TagRepository, TopicRepository
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import Label


class VocabularyResolver:
    def __init__(self, embedding: EmbeddingPort) -> None:
        self._embedding: EmbeddingPort = embedding

    async def resolve_topic(self, _label: Label, _topics: TopicRepository) -> Topic:
        raise NotImplementedError

    async def resolve_tag(self, _label: Label, _tags: TagRepository) -> Tag:
        raise NotImplementedError
