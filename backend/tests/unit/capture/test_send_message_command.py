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
from application.capture.commands.send_message import GenerateReplyCommand
from application.capture.dto import ReplyDoneEvent, ReplyStreamEvent
from application.capture.ports import ConfidenceAssessmentPort
from application.capture.value_objects import (
    ConfidenceAssessment,
    ConfidencePoint,
    ConfidencePointKind,
    Transcript,
)
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
    SessionTopic,
)


async def test_guard_session_raises_not_found_for_unknown_id() -> None:
    stack = _make_command_stack()

    with pytest.raises(CaptureSessionNotFoundError):
        _ = await stack.command.guard_session(SessionId.new(), "Hello there")


async def test_guard_session_raises_closed_for_closed_session() -> None:
    stack = _make_command_stack()
    closed_session = CaptureSession(
        id=SessionId.new(),
        topic=SessionTopic(value="TCP handshakes"),
        status=SessionStatus.CLOSED,
        created_at=datetime.now(UTC),
    )
    await stack.session_repo.save(closed_session)

    with pytest.raises(CaptureSessionClosedError):
        _ = await stack.command.guard_session(
            closed_session.id,
            "Can we continue?",
        )


async def test_guard_session_raises_for_blank_content() -> None:
    stack = _make_command_stack()
    session = CaptureSession.start()
    await stack.session_repo.save(session)

    with pytest.raises(EmptyMessageContentError):
        _ = await stack.command.guard_session(session.id, "   ")


async def test_generate_reply_assigns_topic_on_first_turn_and_streams_done_event() -> (
    None
):
    stack = _make_command_stack()
    session = CaptureSession.start()
    await stack.session_repo.save(session)
    content = MessageContent(value="I want to talk through TCP handshakes")

    events = [event async for event in stack.command.handle(session.id, content)]

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
    session.assign_topic(SessionTopic(value="Existing topic"))
    await stack.session_repo.save(session)
    content = MessageContent(value="Tell me more about the three-way handshake")

    events = [event async for event in stack.command.handle(session.id, content)]

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

    events = [event async for event in stack.command.handle(session.id, content)]

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
        stack.command.handle(session.id, content),
    )
    async with aclosing(stream) as events:
        _ = await anext(events)

    assert stack.store.list_by_session(session.id) == []
    persisted = await stack.session_repo.get(session.id)
    assert persisted is not None
    assert persisted.topic is None


async def test_generate_reply_raises_not_found_if_session_missing_at_handle_time() -> (
    None
):
    stack = _make_command_stack()
    content = MessageContent(value="Hello")

    with pytest.raises(CaptureSessionNotFoundError):
        async for _ in stack.command.handle(SessionId.new(), content):
            pass


async def test_generate_reply_raises_closed_if_session_closed_at_handle_time() -> None:
    stack = _make_command_stack()
    closed = CaptureSession(
        id=SessionId.new(),
        topic=None,
        status=SessionStatus.CLOSED,
        created_at=datetime.now(UTC),
    )
    await stack.session_repo.save(closed)
    content = MessageContent(value="Hello")

    with pytest.raises(CaptureSessionClosedError):
        async for _ in stack.command.handle(closed.id, content):
            pass


async def test_done_event_reports_full_coverage_when_assessment_is_all_solid() -> None:
    stack = _make_command_stack(
        confidence_assessment=_AllSolidConfidenceAssessmentAdapter(),
    )
    session = CaptureSession.start()
    await stack.session_repo.save(session)
    content = MessageContent(value="I think we've covered TCP thoroughly")

    events = [event async for event in stack.command.handle(session.id, content)]

    done = next(event for event in events if isinstance(event, ReplyDoneEvent))
    assert done.coverage_confidence == 1.0


async def test_done_event_reports_zero_coverage_with_deterministic_assessment() -> None:
    stack = _make_command_stack()
    session = CaptureSession.start()
    await stack.session_repo.save(session)
    content = MessageContent(value="Tell me about slow start")

    events = [event async for event in stack.command.handle(session.id, content)]

    done = next(event for event in events if isinstance(event, ReplyDoneEvent))
    assert done.coverage_confidence == 0.0


async def test_full_coverage_does_not_close_session_or_block_follow_up_message() -> (
    None
):
    stack = _make_command_stack(
        confidence_assessment=_AllSolidConfidenceAssessmentAdapter(),
    )
    session = CaptureSession.start()
    await stack.session_repo.save(session)
    first_content = MessageContent(value="We've covered everything about TCP")
    follow_up_content = MessageContent(value="One more thing about retransmission")

    first_events = [
        event async for event in stack.command.handle(session.id, first_content)
    ]
    first_done = next(
        event for event in first_events if isinstance(event, ReplyDoneEvent)
    )
    assert first_done.coverage_confidence == 1.0

    persisted = await stack.session_repo.get(session.id)
    assert persisted is not None
    assert persisted.status == SessionStatus.OPEN

    follow_up_events = [
        event async for event in stack.command.handle(session.id, follow_up_content)
    ]
    follow_up_done = next(
        event for event in follow_up_events if isinstance(event, ReplyDoneEvent)
    )
    assert follow_up_done.content != ""


class _AllSolidConfidenceAssessmentAdapter:
    async def assess(self, transcript: Transcript) -> ConfidenceAssessment:
        _ = transcript
        return ConfidenceAssessment(
            points=[
                ConfidencePoint(
                    kind=ConfidencePointKind.SOLID,
                    note="Topic appears fully covered",
                ),
            ],
            coverage_confidence=1.0,
        )


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


def _make_command_stack(
    confidence_assessment: ConfidenceAssessmentPort | None = None,
) -> _CommandStack:
    store = InMemoryMessageStore()
    session_repo = InMemoryCaptureSessionRepository()
    message_repo = InMemoryMessageRepository(store)
    uow = _SpyUnitOfWork(session_repo, message_repo, store)
    command = GenerateReplyCommand(
        capture_sessions=session_repo,
        uow=uow,  # pyright: ignore[reportArgumentType]
        transcript_query=InMemoryTranscriptQueryAdapter(store),
        topic_extraction=DeterministicTopicExtractionAdapter(),
        confidence_assessment=confidence_assessment
        or DeterministicConfidenceAssessmentAdapter(),
        reply_generation=DeterministicReplyGenerationAdapter(),
    )
    return _CommandStack(store, session_repo, message_repo, uow, command)


class _SpyUnitOfWork(InMemoryUnitOfWork):
    commit_count: int

    def __init__(
        self,
        capture_sessions: InMemoryCaptureSessionRepository,
        messages: InMemoryMessageRepository,
        message_store: InMemoryMessageStore,
    ) -> None:
        super().__init__(capture_sessions, messages, message_store)
        self.commit_count = 0

    @override
    async def commit(self) -> None:
        self.commit_count += 1
        await super().commit()
