from collections.abc import AsyncGenerator
from contextlib import aclosing
from datetime import UTC, datetime
from typing import cast, override

import pytest

from adapters.out.in_memory.capture.capture_session_repository import (
    InMemoryCaptureSessionRepository,
)
from adapters.out.in_memory.capture.confidence_assessment import (
    DeterministicConfidenceAssessmentAdapter,
)
from adapters.out.in_memory.capture.message_repository import (
    InMemoryMessageRepository,
)
from adapters.out.in_memory.capture.message_store import InMemoryMessageStore
from adapters.out.in_memory.capture.reply_generation import (
    DeterministicReplyGenerationAdapter,
)
from adapters.out.in_memory.capture.topic_extraction import (
    DeterministicTopicExtractionAdapter,
)
from adapters.out.in_memory.capture.transcript_query import (
    InMemoryTranscriptQueryAdapter,
)
from adapters.out.in_memory.capture.unit_of_work import InMemoryUnitOfWork
from application.capture.commands.send_message import (
    GenerateReplyCommand,
    load_open_session_for_turn,
)
from application.capture.dto import ReplyDoneEvent, ReplyStreamEvent
from domain.capture.capture_session import CaptureSession
from domain.capture.exceptions import (
    CaptureSessionClosedError,
    CaptureSessionNotFoundError,
    EmptyMessageContentError,
)
from domain.capture.value_objects import (
    MessageContent,
    SessionId,
    SessionStatus,
    Topic,
)


async def test_load_open_session_for_turn_raises_not_found_for_unknown_id() -> None:
    repository = InMemoryCaptureSessionRepository()

    with pytest.raises(CaptureSessionNotFoundError):
        _ = await load_open_session_for_turn(
            SessionId.new(),
            "Hello there",
            repository,
        )


async def test_load_open_session_for_turn_raises_closed_for_closed_session() -> None:
    repository = InMemoryCaptureSessionRepository()
    closed_session = CaptureSession(
        id=SessionId.new(),
        topic=Topic(value="TCP handshakes"),
        status=SessionStatus.CLOSED,
        created_at=datetime.now(UTC),
    )
    await repository.save(closed_session)

    with pytest.raises(CaptureSessionClosedError):
        _ = await load_open_session_for_turn(
            closed_session.id,
            "Can we continue?",
            repository,
        )


async def test_load_open_session_for_turn_raises_for_blank_content() -> None:
    repository = InMemoryCaptureSessionRepository()
    session = CaptureSession.start()
    await repository.save(session)

    with pytest.raises(EmptyMessageContentError):
        _ = await load_open_session_for_turn(session.id, "   ", repository)


async def test_generate_reply_assigns_topic_on_first_turn_and_streams_done_event() -> (
    None
):
    stack = _make_command_stack()
    session = CaptureSession.start()
    await stack.session_repo.save(session)
    content = MessageContent(value="I want to talk through TCP handshakes")

    events = [event async for event in stack.command.handle(session, content)]

    assert any(event.type == "delta" for event in events)
    done = next(event for event in events if isinstance(event, ReplyDoneEvent))
    assert done.topic != ""
    persisted = await stack.session_repo.get(session.id)
    assert persisted is not None
    assert persisted.topic is not None
    assert persisted.topic.value == done.topic


async def test_generate_reply_skips_topic_extraction_on_second_turn() -> None:
    stack = _make_command_stack()
    session = CaptureSession.start()
    session.assign_topic(Topic(value="Existing topic"))
    await stack.session_repo.save(session)
    content = MessageContent(value="Tell me more about the three-way handshake")

    events = [event async for event in stack.command.handle(session, content)]

    done = next(event for event in events if isinstance(event, ReplyDoneEvent))
    assert done.topic == "Existing topic"
    persisted = await stack.session_repo.get(session.id)
    assert persisted is not None
    assert persisted.topic is not None
    assert persisted.topic.value == "Existing topic"


async def test_generate_reply_commits_once_after_stream_drains() -> None:
    stack = _make_command_stack()
    session = CaptureSession.start()
    await stack.session_repo.save(session)
    content = MessageContent(value="Walk me through congestion control")

    events = [event async for event in stack.command.handle(session, content)]

    assert stack.uow.commit_count == 1
    assert any(isinstance(event, ReplyDoneEvent) for event in events)


async def test_generate_reply_rollback_leaves_nothing_persisted_on_early_close() -> (
    None
):
    stack = _make_command_stack()
    session = CaptureSession.start()
    await stack.session_repo.save(session)
    content = MessageContent(value="What is slow start?")

    stream = cast(
        AsyncGenerator[ReplyStreamEvent, None],
        stack.command.handle(session, content),
    )
    async with aclosing(stream) as events:
        _ = await anext(events)

    assert stack.store.list_by_session(session.id) == []
    persisted = await stack.session_repo.get(session.id)
    assert persisted is not None
    assert persisted.topic is None


class _CommandStack:
    store: InMemoryMessageStore
    session_repo: InMemoryCaptureSessionRepository
    message_repo: InMemoryMessageRepository
    uow: "_SpyUnitOfWork"
    command: GenerateReplyCommand

    def __init__(
        self,
        store: InMemoryMessageStore,
        session_repo: InMemoryCaptureSessionRepository,
        message_repo: InMemoryMessageRepository,
        uow: "_SpyUnitOfWork",
        command: GenerateReplyCommand,
    ) -> None:
        self.store = store
        self.session_repo = session_repo
        self.message_repo = message_repo
        self.uow = uow
        self.command = command


def _make_command_stack() -> _CommandStack:
    store = InMemoryMessageStore()
    session_repo = InMemoryCaptureSessionRepository()
    message_repo = InMemoryMessageRepository(store)
    uow = _SpyUnitOfWork(session_repo, message_repo)
    command = GenerateReplyCommand(
        uow=uow,  # pyright: ignore[reportArgumentType]
        transcript_query=InMemoryTranscriptQueryAdapter(store),
        topic_extraction=DeterministicTopicExtractionAdapter(),
        confidence_assessment=DeterministicConfidenceAssessmentAdapter(),
        reply_generation=DeterministicReplyGenerationAdapter(),
    )
    return _CommandStack(store, session_repo, message_repo, uow, command)


class _SpyUnitOfWork(InMemoryUnitOfWork):
    commit_count: int

    def __init__(
        self,
        capture_sessions: InMemoryCaptureSessionRepository,
        messages: InMemoryMessageRepository,
    ) -> None:
        super().__init__(capture_sessions, messages)
        self.commit_count = 0

    @override
    async def commit(self) -> None:
        self.commit_count += 1
        await super().commit()
