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
        _session = cast(AsyncSession, object())
        self.notes = SqlAlchemyNoteRepository(_session)
        self.cards = SqlAlchemyCardRepository(_session)
        self.outbox = SqlAlchemyOutboxAppender(_session)

    async def __aenter__(self) -> "SqlAlchemyDistillUnitOfWork":
        raise NotImplementedError

    async def __aexit__(self, *exc: object) -> None:
        raise NotImplementedError

    async def commit(self) -> None:
        raise NotImplementedError
