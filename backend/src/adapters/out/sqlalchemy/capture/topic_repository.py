from typing import cast

from adapters.out.sqlalchemy.capture.mapping import topic_to_domain, topic_to_row
from adapters.out.sqlalchemy.capture.models import CaptureTopicRow
from domain.capture.topic import Topic
from domain.capture.value_objects import (
    SIMILARITY_SCORE_MAX,
    SIMILARITY_SCORE_MIN,
    Embedding,
    SimilarityScore,
    TopicId,
)
from domain.capture.vocabulary_match import VocabularyMatch
from domain.shared.identity.model import UserId
from sqlalchemy import Double, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyTopicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def add(self, topic: Topic) -> None:
        statement = select(CaptureTopicRow).where(CaptureTopicRow.id == topic.id)
        existing = (await self._session.execute(statement)).scalar_one_or_none()
        updated = topic_to_row(topic)
        if existing is None:
            self._session.add(updated)
        else:
            existing.label = updated.label
            existing.embedding_values = updated.embedding_values
            existing.embedding_model = updated.embedding_model
            existing.created_at = updated.created_at
        await self._session.flush()

    async def get(self, topic_id: TopicId) -> Topic | None:
        statement = select(CaptureTopicRow).where(CaptureTopicRow.id == topic_id)
        row = (await self._session.execute(statement)).scalar_one_or_none()
        return topic_to_domain(row) if row is not None else None

    async def nearest(
        self, owner: UserId, embedding: Embedding
    ) -> VocabularyMatch[Topic] | None:
        distance = CaptureTopicRow.embedding_values.op(
            "<=>", return_type=Double[float]()
        )(embedding.values)
        statement = (
            select(CaptureTopicRow, distance.label("distance"))
            .where(
                CaptureTopicRow.owner_id == owner.value,
                CaptureTopicRow.embedding_model == embedding.model,
                func.vector_dims(CaptureTopicRow.embedding_values)
                == len(embedding.values),
            )
            .order_by(distance, CaptureTopicRow.created_at)
            .limit(1)
        )
        result = (await self._session.execute(statement)).first()
        if result is None:
            return None
        row = cast(CaptureTopicRow, result[0])
        distance_value = cast(float, result[1])
        score = SimilarityScore(value=_clamped_to_score_range(1 - distance_value))
        return VocabularyMatch(entry=topic_to_domain(row), score=score)


def _clamped_to_score_range(value: float) -> float:
    return min(max(value, SIMILARITY_SCORE_MIN), SIMILARITY_SCORE_MAX)
