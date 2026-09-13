import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.in_memory.capture.capture_agent import (
    DeterministicCaptureAgentAdapter,
)
from adapters.out.in_memory.capture.embedding import DeterministicEmbeddingAdapter
from adapters.out.sqlalchemy.capture.capture_session_repository import (
    SqlAlchemyCaptureSessionRepository,
)
from adapters.out.sqlalchemy.capture.message_repository import (
    SqlAlchemyMessageRepository,
)
from adapters.out.sqlalchemy.capture.note_repository import SqlAlchemyNoteRepository
from adapters.out.sqlalchemy.capture.tag_repository import SqlAlchemyTagRepository
from adapters.out.sqlalchemy.capture.topic_repository import (
    SqlAlchemyTopicRepository,
)
from adapters.out.sqlalchemy.capture.unit_of_work import SqlAlchemyCaptureUnitOfWork
from adapters.out.sqlalchemy.engine import create_engine, create_session_factory
from adapters.out.sqlalchemy.shared.outbox.claimer import SqlAlchemyOutboxClaimer
from application.capture.commands.approve_note import ApproveNoteCommand
from application.capture.commands.send_message import GenerateReplyCommand
from application.capture.commands.start_capture_session import (
    StartCaptureSessionCommand,
)
from application.capture.dto import DraftDoneEvent
from application.capture.exceptions import CaptureSessionConflictError
from domain.capture.capture_session import CaptureSession
from domain.capture.message import Message
from domain.capture.note import Note
from domain.capture.outbox import NOTE_APPROVED
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import (
    Embedding,
    Label,
    MessageContent,
    NoteContent,
    NoteId,
    NoteStatus,
    SessionId,
    SessionStatus,
    SessionTopic,
    SimilarityScore,
    TagId,
    TopicId,
)
from domain.capture.vocabulary import MatchCriteria, VocabularyResolver
from domain.shared.outbox.model import OutboxEnvelope

pytestmark = pytest.mark.postgres

_EMBEDDING_MODEL = "test"
_CONFIRMATION = "that's all"
_MATCH = MatchCriteria(threshold=SimilarityScore(value=0.85))


class _ShortLivedCaptureSessionRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def get(self, session_id: SessionId) -> CaptureSession | None:
        async with self._session_factory() as db_session:
            return await SqlAlchemyCaptureSessionRepository(db_session).get(session_id)

    async def save(self, session: CaptureSession) -> None:
        _ = session
        raise NotImplementedError


def _uow(
    session_factory: async_sessionmaker[AsyncSession],
) -> SqlAlchemyCaptureUnitOfWork:
    return SqlAlchemyCaptureUnitOfWork(session_factory)


def _reply_command(
    session_factory: async_sessionmaker[AsyncSession],
    uow: SqlAlchemyCaptureUnitOfWork,
) -> GenerateReplyCommand:
    return GenerateReplyCommand(
        capture_sessions=_ShortLivedCaptureSessionRepository(session_factory),
        uow=uow,  # pyright: ignore[reportArgumentType]
        capture_agent=DeterministicCaptureAgentAdapter(),
        vocabulary=VocabularyResolver(DeterministicEmbeddingAdapter(), _MATCH),
    )


def _sample_topic() -> Topic:
    return Topic.mint(
        Label(value="TCP handshakes"),
        Embedding(model=_EMBEDDING_MODEL, values=(0.1, 0.2)),
    )


def _sample_tag() -> Tag:
    return Tag.mint(
        Label(value="networking"),
        Embedding(model=_EMBEDDING_MODEL, values=(0.3, 0.4)),
    )


async def _load_session(
    session_factory: async_sessionmaker[AsyncSession], session_id: SessionId
) -> CaptureSession | None:
    async with session_factory() as db_session:
        return await SqlAlchemyCaptureSessionRepository(db_session).get(session_id)


async def _load_history(
    session_factory: async_sessionmaker[AsyncSession], session_id: SessionId
) -> list[Message]:
    async with session_factory() as db_session:
        return await SqlAlchemyMessageRepository(db_session).history(session_id)


async def _load_note(
    session_factory: async_sessionmaker[AsyncSession], note_id: NoteId
) -> Note | None:
    async with session_factory() as db_session:
        return await SqlAlchemyNoteRepository(db_session).get(note_id)


async def _load_topic(
    session_factory: async_sessionmaker[AsyncSession], topic_id: TopicId
) -> Topic | None:
    async with session_factory() as db_session:
        return await SqlAlchemyTopicRepository(db_session).get(topic_id)


async def _load_tag(
    session_factory: async_sessionmaker[AsyncSession], tag_id: TagId
) -> Tag | None:
    async with session_factory() as db_session:
        return await SqlAlchemyTagRepository(db_session).get(tag_id)


async def test_started_session_reads_back_equal_through_a_fresh_engine(
    engine: AsyncEngine,
    migrated_database_url: str,
) -> None:
    command = StartCaptureSessionCommand(
        _uow(create_session_factory(engine))  # pyright: ignore[reportArgumentType]
    )
    response = await command.handle()
    session_id = SessionId(value=response.session_id)
    written = await _load_session(create_session_factory(engine), session_id)

    await engine.dispose()
    fresh_engine = create_engine(migrated_database_url)
    try:
        loaded = await _load_session(create_session_factory(fresh_engine), session_id)
        assert loaded == written
    finally:
        await fresh_engine.dispose()


async def test_drafting_generate_reply_turn_is_readable_through_a_fresh_engine(
    engine: AsyncEngine,
    migrated_database_url: str,
) -> None:
    session_factory = create_session_factory(engine)
    uow = _uow(session_factory)
    started = await StartCaptureSessionCommand(
        uow  # pyright: ignore[reportArgumentType]
    ).handle()
    session_id = SessionId(value=started.session_id)
    command = _reply_command(session_factory, uow)
    _ = [
        event
        async for event in command.handle(
            session_id,
            MessageContent(value="Let's talk through TCP handshakes"),
        )
    ]
    events = [
        event
        async for event in command.handle(
            session_id,
            MessageContent(value=_CONFIRMATION),
        )
    ]
    assert any(isinstance(event, DraftDoneEvent) for event in events)

    await engine.dispose()
    fresh_engine = create_engine(migrated_database_url)
    try:
        factory = create_session_factory(fresh_engine)
        session = await _load_session(factory, session_id)
        assert session is not None
        assert session.note_id is not None
        messages = await _load_history(factory, session_id)
        note = await _load_note(factory, session.note_id)
        assert messages
        assert note is not None
        topic = await _load_topic(factory, note.topic_id)
        assert topic is not None
        assert note.tag_ids
        for tag_id in note.tag_ids:
            assert await _load_tag(factory, tag_id) is not None
    finally:
        await fresh_engine.dispose()


async def test_approve_note_commits_note_session_and_claimable_envelope_together(
    engine: AsyncEngine,
    migrated_database_url: str,
) -> None:
    uow = _uow(create_session_factory(engine))
    session = CaptureSession.start()
    topic = _sample_topic()
    tag = _sample_tag()
    note = session.draft_note(
        topic, NoteContent(value="We discussed handshakes."), [tag]
    )
    async with uow:
        await uow.capture_sessions.save(session)
        await uow.topics.add(topic)
        await uow.tags.add(tag)
        await uow.notes.add(note)
        await uow.commit()

    _ = await ApproveNoteCommand(uow).handle(  # pyright: ignore[reportArgumentType]
        session.id
    )

    await engine.dispose()
    fresh_engine = create_engine(migrated_database_url)
    try:
        factory = create_session_factory(fresh_engine)
        persisted_note = await _load_note(factory, note.id)
        persisted_session = await _load_session(factory, session.id)
        claimed = await SqlAlchemyOutboxClaimer(factory).claim(
            NOTE_APPROVED, limit=10, worker_id="w1"
        )
        assert persisted_note is not None
        assert persisted_note.status == NoteStatus.APPROVED
        assert persisted_session is not None
        assert persisted_session.status == SessionStatus.CLOSED
        assert len(claimed) == 1
        assert claimed[0].payload["note_id"] == str(note.id.value)
    finally:
        await fresh_engine.dispose()


async def test_exception_after_session_note_and_envelope_leaves_none_persisted(
    engine: AsyncEngine,
    migrated_database_url: str,
) -> None:
    uow = _uow(create_session_factory(engine))
    session = CaptureSession.start()
    topic = _sample_topic()
    tag = _sample_tag()
    note = session.draft_note(
        topic, NoteContent(value="We discussed handshakes."), [tag]
    )
    envelope = OutboxEnvelope.pending(NOTE_APPROVED, {"note_id": str(note.id.value)})

    with pytest.raises(RuntimeError, match="boom"):
        async with uow:
            await uow.capture_sessions.save(session)
            await uow.topics.add(topic)
            await uow.tags.add(tag)
            await uow.notes.add(note)
            await uow.outbox.append(envelope)
            raise RuntimeError("boom")

    await engine.dispose()
    fresh_engine = create_engine(migrated_database_url)
    try:
        factory = create_session_factory(fresh_engine)
        claimed = await SqlAlchemyOutboxClaimer(factory).claim(
            NOTE_APPROVED, limit=10, worker_id="w1"
        )
        assert await _load_session(factory, session.id) is None
        assert await _load_note(factory, note.id) is None
        assert claimed == []
    finally:
        await fresh_engine.dispose()


async def test_stale_session_save_raises_conflict_and_leaves_the_committed_write(
    engine: AsyncEngine,
    migrated_database_url: str,
) -> None:
    factory = create_session_factory(engine)
    session = CaptureSession.start()
    async with SqlAlchemyCaptureUnitOfWork(factory) as seed:
        await seed.capture_sessions.save(session)
        await seed.commit()

    loser = SqlAlchemyCaptureUnitOfWork(factory)
    winner = SqlAlchemyCaptureUnitOfWork(factory)
    async with loser:
        stale = await loser.capture_sessions.get(session.id)
        async with winner:
            concurrent = await winner.capture_sessions.get(session.id)
            assert concurrent is not None
            concurrent.assign_topic(SessionTopic(value="winner topic"))
            await winner.capture_sessions.save(concurrent)
            await winner.commit()
        assert stale is not None
        stale.assign_topic(SessionTopic(value="loser topic"))
        with pytest.raises(CaptureSessionConflictError):
            await loser.capture_sessions.save(stale)
            await loser.commit()

    await engine.dispose()
    fresh_engine = create_engine(migrated_database_url)
    try:
        loaded = await _load_session(create_session_factory(fresh_engine), session.id)
        assert loaded is not None
        assert loaded.topic == SessionTopic(value="winner topic")
    finally:
        await fresh_engine.dispose()
