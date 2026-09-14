from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from adapters.out.sqlalchemy.engine import create_session_factory
from adapters.out.sqlalchemy.remember.models import (
    RememberReviewEventRow,
    RememberSittingRow,
)
from domain.remember.value_objects import CardId, ResumeHorizon, ShowingLimit, SittingId

pytestmark = pytest.mark.postgres


async def test_graded_event_row_with_null_grade_is_rejected_by_grade_iff_graded_check(
    engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(engine)
    sitting_id = SittingId(value=uuid4())
    card_id = CardId(value=uuid4())
    opened_at = datetime.now(UTC)

    async with session_factory() as db_session:
        db_session.add(
            RememberSittingRow(
                id=sitting_id,
                owner_id=uuid4(),
                opened_at=opened_at,
                showing_limit=ShowingLimit(value=2),
                resume_horizon=ResumeHorizon(value=timedelta(days=1)),
            )
        )
        await db_session.flush()
        db_session.add(
            RememberReviewEventRow(
                sitting_id=sitting_id,
                card_id=card_id,
                reviewed_at=opened_at,
                kind="graded",
                grade=None,
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.flush()


async def test_review_event_for_an_unknown_sitting_is_rejected_by_foreign_key(
    engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(engine)
    missing_sitting_id = SittingId(value=uuid4())
    card_id = CardId(value=uuid4())
    reviewed_at = datetime.now(UTC)

    async with session_factory() as db_session:
        db_session.add(
            RememberReviewEventRow(
                sitting_id=missing_sitting_id,
                card_id=card_id,
                reviewed_at=reviewed_at,
                kind="rejected",
                grade=None,
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.flush()
