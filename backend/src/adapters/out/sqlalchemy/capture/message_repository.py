from domain.capture.message import Message
from domain.capture.value_objects import SessionId
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def add(self, message: Message) -> None:
        _ = message
        raise NotImplementedError

    async def history(self, session_id: SessionId) -> list[Message]:
        _ = session_id
        raise NotImplementedError
