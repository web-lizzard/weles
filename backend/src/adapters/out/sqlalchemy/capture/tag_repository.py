from typing import cast

from adapters.out.sqlalchemy.capture.mapping import tag_to_domain, tag_to_row
from adapters.out.sqlalchemy.capture.models import CaptureTagRow
from domain.capture.tag import Tag
from domain.capture.value_objects import (
    SIMILARITY_SCORE_MAX,
    SIMILARITY_SCORE_MIN,
    Embedding,
    SimilarityScore,
    TagId,
)
from domain.capture.vocabulary_match import VocabularyMatch
from sqlalchemy import Double, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyTagRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def add(self, tag: Tag) -> None:
        statement = select(CaptureTagRow).where(CaptureTagRow.id == tag.id)
        existing = (await self._session.execute(statement)).scalar_one_or_none()
        updated = tag_to_row(tag)
        if existing is None:
            self._session.add(updated)
        else:
            existing.label = updated.label
            existing.embedding_values = updated.embedding_values
            existing.embedding_model = updated.embedding_model
            existing.created_at = updated.created_at
        await self._session.flush()

    async def get(self, tag_id: TagId) -> Tag | None:
        statement = select(CaptureTagRow).where(CaptureTagRow.id == tag_id)
        row = (await self._session.execute(statement)).scalar_one_or_none()
        return tag_to_domain(row) if row is not None else None

    async def nearest(self, embedding: Embedding) -> VocabularyMatch[Tag] | None:
        distance = CaptureTagRow.embedding_values.op(
            "<=>", return_type=Double[float]()
        )(embedding.values)
        statement = (
            select(CaptureTagRow, distance.label("distance"))
            .where(
                CaptureTagRow.embedding_model == embedding.model,
                func.vector_dims(CaptureTagRow.embedding_values)
                == len(embedding.values),
            )
            .order_by(distance, CaptureTagRow.created_at)
            .limit(1)
        )
        result = (await self._session.execute(statement)).first()
        if result is None:
            return None
        row = cast(CaptureTagRow, result[0])
        distance_value = cast(float, result[1])
        score = SimilarityScore(value=_clamped_to_score_range(1 - distance_value))
        return VocabularyMatch(entry=tag_to_domain(row), score=score)


def _clamped_to_score_range(value: float) -> float:
    return min(max(value, SIMILARITY_SCORE_MIN), SIMILARITY_SCORE_MAX)
