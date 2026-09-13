import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from adapters.out.sqlalchemy.capture.message_repository import (
    SqlAlchemyMessageRepository,
)
from adapters.out.sqlalchemy.engine import create_session_factory
from domain.capture.message import Message
from domain.capture.value_objects import MessageContent, MessageRole, SessionId

pytestmark = pytest.mark.postgres


async def test_add_message_without_session_row_is_rejected_by_postgres(
    engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(engine)
    message = Message.record(
        session_id=SessionId.new(),
        role=MessageRole.USER,
        content=MessageContent(value="Orphan message"),
    )

    async with session_factory() as db_session:
        repository = SqlAlchemyMessageRepository(db_session)
        with pytest.raises(IntegrityError):
            await repository.add(message)
            await db_session.commit()
