from typing import cast

from adapters.out.sqlalchemy.distill.card_repository import SqlAlchemyCardRepository
from adapters.out.sqlalchemy.distill.note_repository import SqlAlchemyNoteRepository
from adapters.out.sqlalchemy.shared.outbox.appender import SqlAlchemyOutboxAppender
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlAlchemyDistillUnitOfWork:
    notes: SqlAlchemyNoteRepository
    cards: SqlAlchemyCardRepository
    outbox: SqlAlchemyOutboxAppender

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory
        self._committed: bool = False
        self._session: AsyncSession | None = None
        _session = cast(AsyncSession, object())
        self.notes = SqlAlchemyNoteRepository(_session)
        self.cards = SqlAlchemyCardRepository(_session)
        self.outbox = SqlAlchemyOutboxAppender(_session)

    async def __aenter__(self) -> "SqlAlchemyDistillUnitOfWork":
        self._committed = False
        session = self._session_factory()
        self._session = session
        self.notes = SqlAlchemyNoteRepository(session)
        self.cards = SqlAlchemyCardRepository(session)
        self.outbox = SqlAlchemyOutboxAppender(session)
        return self

    async def __aexit__(self, *exc: object) -> None:
        session = self._session
        if session is None:
            return
        try:
            if not self._committed:
                await session.rollback()
        finally:
            await session.close()
            self._session = None

    async def commit(self) -> None:
        session = self._session
        assert session is not None
        await session.commit()
        self._committed = True
