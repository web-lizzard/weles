from domain.capture.topic import Topic
from domain.capture.value_objects import Embedding, TopicId
from domain.capture.vocabulary_match import VocabularyMatch
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyTopicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def add(self, topic: Topic) -> None:
        _ = topic
        raise NotImplementedError

    async def get(self, topic_id: TopicId) -> Topic | None:
        _ = topic_id
        raise NotImplementedError

    async def nearest(self, embedding: Embedding) -> VocabularyMatch[Topic] | None:
        _ = embedding
        raise NotImplementedError
