from typing import cast

from adapters.out.sqlalchemy.capture.capture_session_repository import (
    SqlAlchemyCaptureSessionRepository,
)
from adapters.out.sqlalchemy.capture.message_repository import (
    SqlAlchemyMessageRepository,
)
from adapters.out.sqlalchemy.capture.note_repository import SqlAlchemyNoteRepository
from adapters.out.sqlalchemy.capture.note_vocabulary_repository import (
    SqlAlchemyNoteVocabularyRepository,
)
from adapters.out.sqlalchemy.capture.tag_repository import SqlAlchemyTagRepository
from adapters.out.sqlalchemy.capture.topic_repository import (
    SqlAlchemyTopicRepository,
)
from adapters.out.sqlalchemy.shared.outbox.appender import SqlAlchemyOutboxAppender
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlAlchemyCaptureUnitOfWork:
    capture_sessions: SqlAlchemyCaptureSessionRepository
    messages: SqlAlchemyMessageRepository
    notes: SqlAlchemyNoteRepository
    topics: SqlAlchemyTopicRepository
    tags: SqlAlchemyTagRepository
    note_vocabulary: SqlAlchemyNoteVocabularyRepository
    outbox: SqlAlchemyOutboxAppender

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory
        self._committed: bool = False
        self._session: AsyncSession | None = None
        _session = cast(AsyncSession, object())
        self.capture_sessions = SqlAlchemyCaptureSessionRepository(_session)
        self.messages = SqlAlchemyMessageRepository(_session)
        self.notes = SqlAlchemyNoteRepository(_session)
        self.topics = SqlAlchemyTopicRepository(_session)
        self.tags = SqlAlchemyTagRepository(_session)
        self.note_vocabulary = SqlAlchemyNoteVocabularyRepository(_session)
        self.outbox = SqlAlchemyOutboxAppender(_session)

    async def __aenter__(self) -> "SqlAlchemyCaptureUnitOfWork":
        self._committed = False
        session = self._session_factory()
        self._session = session
        self.capture_sessions = SqlAlchemyCaptureSessionRepository(session)
        self.messages = SqlAlchemyMessageRepository(session)
        self.notes = SqlAlchemyNoteRepository(session)
        self.topics = SqlAlchemyTopicRepository(session)
        self.tags = SqlAlchemyTagRepository(session)
        self.note_vocabulary = SqlAlchemyNoteVocabularyRepository(session)
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
