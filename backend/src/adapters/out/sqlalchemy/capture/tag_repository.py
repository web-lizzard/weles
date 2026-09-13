from domain.capture.tag import Tag
from domain.capture.value_objects import Embedding, TagId
from domain.capture.vocabulary_match import VocabularyMatch
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyTagRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def add(self, tag: Tag) -> None:
        _ = tag
        raise NotImplementedError

    async def get(self, tag_id: TagId) -> Tag | None:
        _ = tag_id
        raise NotImplementedError

    async def nearest(self, embedding: Embedding) -> VocabularyMatch[Tag] | None:
        _ = embedding
        raise NotImplementedError
