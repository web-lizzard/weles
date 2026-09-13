from adapters.out.sqlalchemy.capture.mapping import message_to_domain, message_to_row
from adapters.out.sqlalchemy.capture.models import CaptureMessageRow
from domain.capture.message import Message
from domain.capture.value_objects import SessionId
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def add(self, message: Message) -> None:
        self._session.add(message_to_row(message))
        await self._session.flush()

    async def history(self, session_id: SessionId) -> list[Message]:
        statement = (
            select(CaptureMessageRow)
            .where(CaptureMessageRow.session_id == session_id)
            .order_by(CaptureMessageRow.position)
        )
        rows = (await self._session.execute(statement)).scalars().all()
        return [message_to_domain(row) for row in rows]
