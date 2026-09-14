from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from adapters.out.sqlalchemy.distill.card_repository import SqlAlchemyCardRepository
from adapters.out.sqlalchemy.distill.models import DistillCardRow, DistillNoteRow
from adapters.out.sqlalchemy.engine import create_session_factory
from domain.distill.card import Card
from domain.distill.value_objects import (
    Anchor,
    CardId,
    CardSide,
    DiscardReason,
    DistillationStatus,
    NoteContent,
    NoteId,
    SessionId,
)
from domain.shared.identity.model import UserId

pytestmark = pytest.mark.postgres


def _orphan_card() -> Card:
    return Card(
        id=CardId(value=uuid4()),
        owner_id=UserId.new(),
        note_id=NoteId(value=uuid4()),
        front=CardSide(value="Front"),
        back=CardSide(value="Back"),
        anchor=Anchor(quote="Anchor quote"),
        discard=None,
        created_at=datetime.now(UTC),
    )


async def test_save_card_without_note_row_is_rejected_by_postgres(
    engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(engine)
    card = _orphan_card()

    async with session_factory() as db_session:
        repository = SqlAlchemyCardRepository(db_session)
        with pytest.raises(IntegrityError):
            await repository.save(card)
            await db_session.flush()


async def test_incomplete_discard_row_is_rejected_by_discard_complete_check(
    engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(engine)
    note_id = NoteId(value=uuid4())
    card_id = CardId(value=uuid4())
    stamped_at = datetime.now(UTC)

    async with session_factory() as db_session:
        db_session.add(
            DistillNoteRow(
                id=note_id,
                owner_id=uuid4(),
                session_id=SessionId(value=uuid4()),
                topic_id=uuid4(),
                topic_label="topic",
                content=NoteContent(value="Note body"),
                distillation_status=DistillationStatus.GENERATING,
                approved_at=stamped_at,
                created_at=stamped_at,
                updated_at=stamped_at,
            )
        )
        await db_session.flush()
        db_session.add(
            DistillCardRow(
                id=card_id,
                owner_id=uuid4(),
                note_id=note_id,
                front=CardSide(value="Front"),
                back=CardSide(value="Back"),
                anchor_quote=Anchor(quote="Quote"),
                discard_reason=DiscardReason.UNGROUNDED,
                discard_detail=None,
                discarded_at=None,
                created_at=stamped_at,
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.flush()
