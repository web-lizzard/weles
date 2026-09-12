from collections.abc import AsyncGenerator, AsyncIterator, Callable, Sequence
from contextlib import aclosing, asynccontextmanager
from datetime import UTC, datetime
from typing import cast, override

import pytest

from adapters.out.in_memory.capture.capture_agent import (
    DeterministicCaptureAgentAdapter,
)
from adapters.out.in_memory.capture.capture_session_repository import (
    InMemoryCaptureSessionRepository,
)
from adapters.out.in_memory.capture.embedding import DeterministicEmbeddingAdapter
from adapters.out.in_memory.capture.message_repository import (
    InMemoryMessageRepository,
)
from adapters.out.in_memory.capture.message_store import InMemoryMessageStore
from adapters.out.in_memory.capture.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.capture.note_vocabulary_repository import (
    InMemoryNoteVocabularyRepository,
)
from adapters.out.in_memory.capture.tag_repository import InMemoryTagRepository
from adapters.out.in_memory.capture.topic_repository import InMemoryTopicRepository
from adapters.out.in_memory.capture.unit_of_work import InMemoryUnitOfWork
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from application.capture.commands.send_message import GenerateReplyCommand
from application.capture.dto import (
    DraftDoneEvent,
    DraftTagEvent,
    DraftTopicEvent,
    ReplyDoneEvent,
    ReplyStreamEvent,
)
from application.capture.services.vocabulary import VocabularyResolver
from domain.capture.capture_session import CaptureSession
from domain.capture.exceptions import (
    CaptureSessionClosedError,
    CaptureSessionNotFoundError,
    EmptyMessageContentError,
)
from domain.capture.turn import (
    AgentEvent,
    CaptureTurn,
    ConversationRequested,
    DraftingConsentSignalled,
    NoteContentProduced,
    NoteTagProposed,
    NoteTopicProposed,
    ReplyProduced,
)
from domain.capture.value_objects import (
    CapturePhase,
    Label,
    MessageContent,
    NoteContent,
    NoteStatus,
    SessionId,
    SessionStatus,
    SessionTopic,
    SimilarityScore,
)
from domain.capture.vocabulary import MatchCriteria
from domain.exceptions import CoreException
from domain.shared.graph.model import Tool, ToolResult

_CONFIRMATION_PHRASE = "that's all"


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
    stack = _make_command_stack(capture_agent=_FullCoverageCaptureAgent())
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


async def test_drafting_turn_emits_draft_events_before_done() -> None:
    stack = _make_command_stack()
    session = await _start_session_with_topic(stack, "TCP handshakes")

    events = await _handle_confirmation_turn(stack, session)

    _assert_drafting_event_sequence(events)


async def test_drafting_turn_forwards_tag_reused_flag_from_resolver() -> None:
    stack = _make_agent_command_stack(
        _consent_then_draft_agent(
            _draft_events(
                topic=Label(value="topic"),
                tags=[Label(value="networking"), Label(value="networking")],
                contents=["note body"],
            )
        )
    )
    session = CaptureSession.start()
    session.assign_topic(SessionTopic(value="TCP handshakes"))
    await stack.session_repo.save(session)

    events = await _handle_confirmation_turn(stack, session)

    draft_tag_events = [event for event in events if isinstance(event, DraftTagEvent)]
    assert len(draft_tag_events) == 2
    assert draft_tag_events[0].reused is False
    assert draft_tag_events[1].reused is True


async def test_drafting_turn_persists_note_and_links_session_note_id() -> None:
    stack = _make_command_stack()
    session = await _start_session_with_topic(stack, "TCP handshakes")

    events = await _handle_confirmation_turn(stack, session)

    draft_done = next(event for event in events if isinstance(event, DraftDoneEvent))
    persisted_session = await stack.session_repo.get(session.id)
    assert persisted_session is not None
    assert persisted_session.note_id is not None

    note = await stack.uow.notes.get(persisted_session.note_id)
    assert note is not None
    assert note.status == NoteStatus.DRAFT
    assert note.id.value == draft_done.note_id

    topic = await stack.uow.topics.get(note.topic_id)
    assert topic is not None
    assert topic.label.value == draft_done.topic

    tag_labels: list[str] = []
    for tag_id in note.tag_ids:
        tag = await stack.uow.tags.get(tag_id)
        assert tag is not None
        tag_labels.append(tag.label.value)
    assert tag_labels == draft_done.tags


async def test_drafting_mid_stream_failure_rolls_back_draft_artifacts() -> None:
    agent = _ScriptedCaptureAgent(
        [
            [ReplyProduced(text="Let's continue.")],
            [DraftingConsentSignalled()],
            [
                ReplyProduced(text="handoff"),
                NoteTopicProposed(label=Label(value="TCP handshakes")),
                NoteTagProposed(label=Label(value="networking")),
                _RAISE,
            ],
        ]
    )
    stack = _make_agent_command_stack(agent)
    session = await _start_session_with_topic(stack, "TCP handshakes")
    message_count_before = len(stack.store.list_by_session(session.id))

    with pytest.raises(RuntimeError, match="simulated mid-stream failure"):
        async for _ in stack.command.handle(
            session.id,
            MessageContent(value=_CONFIRMATION_PHRASE),
        ):
            pass

    assert len(stack.uow.notes.snapshot()) == 0
    assert len(stack.uow.topics.snapshot()) == 0
    assert len(stack.uow.tags.snapshot()) == 0
    assert len(stack.store.list_by_session(session.id)) == message_count_before
    persisted = await stack.session_repo.get(session.id)
    assert persisted is not None
    assert persisted.note_id is None


async def test_second_confirmation_turn_redrafts_note_keeping_same_id() -> None:
    stack = _make_command_stack()
    session = await _start_session_with_topic(stack, "TCP handshakes")
    first_events = await _handle_confirmation_turn(stack, session)
    first_draft_done = next(
        event for event in first_events if isinstance(event, DraftDoneEvent)
    )

    second_events = await _handle_confirmation_turn(stack, session)

    second_draft_done = next(
        event for event in second_events if isinstance(event, DraftDoneEvent)
    )
    assert second_draft_done.note_id == first_draft_done.note_id
    persisted_session = await stack.session_repo.get(session.id)
    assert persisted_session is not None
    assert persisted_session.note_id is not None
    assert persisted_session.note_id.value == first_draft_done.note_id


async def test_redraft_turn_updates_topic_tags_and_content_keeping_same_note_id() -> (
    None
):
    stack = _make_agent_command_stack(
        _ScriptedCaptureAgent(
            [
                [DraftingConsentSignalled()],
                _draft_events(
                    topic=Label(value="TCP handshakes"),
                    tags=[Label(value="networking")],
                    contents=["original body"],
                ),
                _draft_events(
                    topic=Label(value="congestion control"),
                    tags=[Label(value="performance")],
                    contents=["revised body"],
                ),
            ]
        )
    )
    session = CaptureSession.start()
    session.assign_topic(SessionTopic(value="TCP handshakes"))
    await stack.session_repo.save(session)

    first_events = await _handle_confirmation_turn(stack, session)
    first_draft_done = next(
        event for event in first_events if isinstance(event, DraftDoneEvent)
    )

    second_events = [
        event
        async for event in stack.command.handle(
            session.id,
            MessageContent(value="Make it about congestion control instead"),
        )
    ]
    second_draft_done = next(
        event for event in second_events if isinstance(event, DraftDoneEvent)
    )

    assert second_draft_done.note_id == first_draft_done.note_id
    assert second_draft_done.topic == "congestion control"
    assert second_draft_done.content == "revised body"
    assert second_draft_done.tags == ["performance"]

    persisted_session = await stack.session_repo.get(session.id)
    assert persisted_session is not None
    assert persisted_session.note_id is not None
    assert persisted_session.note_id.value == first_draft_done.note_id
    note = await stack.uow.notes.get(persisted_session.note_id)
    assert note is not None
    assert note.status == NoteStatus.DRAFT
    topic = await stack.uow.topics.get(note.topic_id)
    assert topic is not None
    assert topic.label.value == "congestion control"


async def test_redraft_removes_dropped_tags_from_persisted_note_R2_F4() -> None:
    """R2-F4: redraft must remove tags absent from the turn's resolved set."""
    stack = _make_agent_command_stack(
        _ScriptedCaptureAgent(
            [
                [DraftingConsentSignalled()],
                _draft_events(
                    topic=Label(value="TCP handshakes"),
                    tags=[Label(value="networking")],
                    contents=["original body"],
                ),
                _draft_events(
                    topic=Label(value="congestion control"),
                    tags=[Label(value="performance")],
                    contents=["revised body"],
                ),
            ]
        )
    )
    session = CaptureSession.start()
    session.assign_topic(SessionTopic(value="TCP handshakes"))
    await stack.session_repo.save(session)

    _ = await _handle_confirmation_turn(stack, session)
    second_events = [
        event
        async for event in stack.command.handle(
            session.id,
            MessageContent(value="Make it about congestion control instead"),
        )
    ]
    second_draft_done = next(
        event for event in second_events if isinstance(event, DraftDoneEvent)
    )

    persisted_session = await stack.session_repo.get(session.id)
    assert persisted_session is not None
    assert persisted_session.note_id is not None
    note = await stack.uow.notes.get(persisted_session.note_id)
    assert note is not None
    assert len(note.tag_ids) == len(second_draft_done.tags)
    persisted_tags: list[str] = []
    for tag_id in note.tag_ids:
        tag = await stack.uow.tags.get(tag_id)
        assert tag is not None
        persisted_tags.append(tag.label.value)
    assert persisted_tags == second_draft_done.tags


async def test_draft_content_accumulates_across_multiple_chunks() -> None:
    """R2-F6: two note content chunks in one turn concatenate on note and event."""
    stack = _make_agent_command_stack(
        _consent_then_draft_agent(
            [
                ReplyProduced(text="handoff"),
                NoteTopicProposed(label=Label(value="topic")),
                NoteContentProduced(content=NoteContent(value="first part")),
                NoteContentProduced(content=NoteContent(value=" second part")),
            ]
        )
    )
    session = CaptureSession.start()
    session.assign_topic(SessionTopic(value="TCP handshakes"))
    await stack.session_repo.save(session)

    events = await _handle_confirmation_turn(stack, session)

    draft_done = next(event for event in events if isinstance(event, DraftDoneEvent))
    expected_content = "first partsecond part"
    assert draft_done.content == expected_content

    persisted_session = await stack.session_repo.get(session.id)
    assert persisted_session is not None
    assert persisted_session.note_id is not None
    note = await stack.uow.notes.get(persisted_session.note_id)
    assert note is not None
    assert note.content.value == expected_content


async def test_redraft_adds_new_tags_to_persisted_note_R2_F5() -> None:
    """R2-F5: redraft must add tags present in the turn but missing on the note."""
    stack = _make_agent_command_stack(
        _ScriptedCaptureAgent(
            [
                [DraftingConsentSignalled()],
                _draft_events(
                    topic=Label(value="TCP handshakes"),
                    contents=["original body"],
                ),
                _draft_events(
                    topic=Label(value="TCP handshakes"),
                    tags=[Label(value="performance")],
                    contents=["revised body"],
                ),
            ]
        )
    )
    session = CaptureSession.start()
    session.assign_topic(SessionTopic(value="TCP handshakes"))
    await stack.session_repo.save(session)

    _ = await _handle_confirmation_turn(stack, session)
    second_events = [
        event
        async for event in stack.command.handle(
            session.id,
            MessageContent(value="Add a performance tag"),
        )
    ]
    second_draft_done = next(
        event for event in second_events if isinstance(event, DraftDoneEvent)
    )

    persisted_session = await stack.session_repo.get(session.id)
    assert persisted_session is not None
    assert persisted_session.note_id is not None
    note = await stack.uow.notes.get(persisted_session.note_id)
    assert note is not None
    assert len(note.tag_ids) == 1
    tag = await stack.uow.tags.get(note.tag_ids[0])
    assert tag is not None
    assert tag.label.value == second_draft_done.tags[0]


async def test_conversational_turn_emits_only_delta_and_done_events() -> None:
    stack = _make_command_stack()
    session = CaptureSession.start()
    await stack.session_repo.save(session)
    content = MessageContent(value="Explain TCP handshakes")

    events = [event async for event in stack.command.handle(session.id, content)]

    event_types = [event.type for event in events]
    assert event_types.count("delta") >= 1
    assert event_types[-1] == "done"
    assert "draft_topic" not in event_types
    assert "draft_tag" not in event_types
    assert "draft_delta" not in event_types
    assert "draft_done" not in event_types


async def test_full_coverage_does_not_close_session_or_block_follow_up_message() -> (
    None
):
    stack = _make_command_stack(capture_agent=_FullCoverageCaptureAgent())
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


async def test_draft_done_content_matches_persisted_note_content() -> None:
    stack = _make_agent_command_stack(
        _consent_then_draft_agent(
            _draft_events(
                topic=Label(value="topic"),
                contents=["  padded body  "],
            )
        )
    )
    session = CaptureSession.start()
    session.assign_topic(SessionTopic(value="TCP handshakes"))
    await stack.session_repo.save(session)

    events = await _handle_confirmation_turn(stack, session)

    draft_done = next(event for event in events if isinstance(event, DraftDoneEvent))
    persisted_session = await stack.session_repo.get(session.id)
    assert persisted_session is not None
    assert persisted_session.note_id is not None
    note = await stack.uow.notes.get(persisted_session.note_id)
    assert note is not None
    assert draft_done.content == note.content.value


async def test_draft_tag_without_prior_topic_raises_core_exception() -> None:
    stack = _make_agent_command_stack(
        _consent_then_draft_agent(
            [
                ReplyProduced(text="handoff"),
                NoteTagProposed(label=Label(value="orphan-tag")),
            ]
        )
    )
    session = CaptureSession.start()
    session.assign_topic(SessionTopic(value="TCP handshakes"))
    await stack.session_repo.save(session)

    with pytest.raises(CoreException):
        async for _ in stack.command.handle(
            session.id,
            MessageContent(value=_CONFIRMATION_PHRASE),
        ):
            pass


async def test_ordinary_turn_opens_one_converse_segment_and_stays_conversing() -> None:
    agent = _ScriptedCaptureAgent(
        [
            [ReplyProduced(text="Let's unpack the handshake.")],
        ]
    )
    stack = _make_agent_command_stack(agent)
    session = CaptureSession.start()
    await stack.session_repo.save(session)

    events = [
        event
        async for event in stack.command.handle(
            session.id,
            MessageContent(value="Explain TCP handshakes"),
        )
    ]

    assert agent.converse_calls == 1
    event_types = [event.type for event in events]
    assert "delta" in event_types
    assert event_types[-1] == "done"
    assert "draft_topic" not in event_types
    persisted = await stack.session_repo.get(session.id)
    assert persisted is not None
    assert persisted.phase is CapturePhase.CONVERSING


async def test_consent_turn_runs_two_segments_streaming_reply_then_draft() -> None:
    agent = _ScriptedCaptureAgent(
        [
            [
                ReplyProduced(text="handoff"),
                DraftingConsentSignalled(),
            ],
            [
                NoteTopicProposed(label=Label(value="TCP handshakes")),
                NoteTagProposed(label=Label(value="networking")),
                NoteContentProduced(content=NoteContent(value="SYN then ACK.")),
            ],
        ]
    )
    stack = _make_agent_command_stack(agent)
    session = CaptureSession.start()
    session.assign_topic(SessionTopic(value="TCP handshakes"))
    await stack.session_repo.save(session)

    events = [
        event
        async for event in stack.command.handle(
            session.id,
            MessageContent(value=_CONFIRMATION_PHRASE),
        )
    ]

    assert agent.converse_calls == 2
    event_types = [event.type for event in events]
    assert event_types.index("delta") < event_types.index("draft_topic")
    assert "draft_done" in event_types
    persisted = await stack.session_repo.get(session.id)
    assert persisted is not None
    assert persisted.phase is CapturePhase.DRAFTING
    assert persisted.note_id is not None


async def test_no_turn_opens_three_segments_even_when_a_move_remains() -> None:
    agent = _OscillatingCaptureAgent()
    stack = _make_agent_command_stack(agent)
    session = CaptureSession.start()
    await stack.session_repo.save(session)

    events = [
        event
        async for event in stack.command.handle(
            session.id,
            MessageContent(value=_CONFIRMATION_PHRASE),
        )
    ]

    assert agent.converse_calls == 2
    assert any(isinstance(event, ReplyDoneEvent) for event in events)


async def test_mid_stream_agent_failure_rolls_back_the_uncommitted_turn() -> None:
    agent = _ScriptedCaptureAgent(
        [
            [ReplyProduced(text="partial"), _RAISE],
        ]
    )
    stack = _make_agent_command_stack(agent)
    session = CaptureSession.start()
    await stack.session_repo.save(session)

    with pytest.raises(RuntimeError, match="simulated mid-stream failure"):
        async for _ in stack.command.handle(
            session.id,
            MessageContent(value="What is slow start?"),
        ):
            pass

    assert stack.store.list_by_session(session.id) == []
    persisted = await stack.session_repo.get(session.id)
    assert persisted is not None
    assert persisted.topic is None
    assert persisted.phase is CapturePhase.CONVERSING
    assert stack.uow.commit_count == 0


def _draft_events(
    *,
    topic: Label,
    tags: list[Label] | None = None,
    contents: list[str],
    reply_text: str = "handoff",
) -> list[object]:
    events: list[object] = [
        ReplyProduced(text=reply_text),
        NoteTopicProposed(label=topic),
    ]
    for tag in tags or []:
        events.append(NoteTagProposed(label=tag))
    for text in contents:
        events.append(NoteContentProduced(content=NoteContent(value=text)))
    return events


class _FullCoverageCaptureAgent(DeterministicCaptureAgentAdapter):
    @asynccontextmanager
    async def converse(
        self,
        turn: CaptureTurn,
        tools: Sequence[Tool[CaptureTurn, ToolResult]],
    ) -> AsyncGenerator[AsyncIterator[AgentEvent], None]:
        async with super().converse(turn, tools) as events:

            async def with_full_coverage() -> AsyncGenerator[AgentEvent, None]:
                async for event in events:
                    yield event
                turn.coverage_confidence = 1.0

            yield with_full_coverage()


def _assert_drafting_event_sequence(events: list[ReplyStreamEvent]) -> None:
    event_types = [event.type for event in events]

    draft_topic_index = event_types.index("draft_topic")
    assert draft_topic_index >= 1
    assert all(event_type == "delta" for event_type in event_types[:draft_topic_index])

    draft_done_index = event_types.index("draft_done")
    done_index = event_types.index("done")
    assert done_index == len(event_types) - 1
    assert draft_done_index < done_index

    draft_delta_indices = [
        index
        for index, event_type in enumerate(event_types)
        if event_type == "draft_delta"
    ]
    first_draft_delta_index = (
        draft_delta_indices[0] if draft_delta_indices else draft_done_index
    )
    middle_types = event_types[draft_topic_index + 1 : first_draft_delta_index]
    assert all(event_type == "draft_tag" for event_type in middle_types)

    if draft_delta_indices:
        assert all(
            event_type == "draft_delta"
            for event_type in event_types[first_draft_delta_index:draft_done_index]
        )

    assert isinstance(events[draft_topic_index], DraftTopicEvent)
    assert all(
        isinstance(event, DraftTagEvent)
        for event in events[draft_topic_index + 1 : first_draft_delta_index]
    )
    assert isinstance(events[draft_done_index], DraftDoneEvent)
    assert isinstance(events[done_index], ReplyDoneEvent)


async def _start_session_with_topic(
    stack: "_CommandStack",
    topic: str,
) -> CaptureSession:
    session = CaptureSession.start()
    await stack.session_repo.save(session)
    _ = [
        event
        async for event in stack.command.handle(
            session.id,
            MessageContent(value=f"Let's talk through {topic}"),
        )
    ]
    return session


async def _handle_confirmation_turn(
    stack: "_CommandStack",
    session: CaptureSession,
) -> list[ReplyStreamEvent]:
    return [
        event
        async for event in stack.command.handle(
            session.id,
            MessageContent(value=_CONFIRMATION_PHRASE),
        )
    ]


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


_RAISE = object()


class _ScriptedCaptureAgent:
    converse_calls: int
    _scripts: list[list[object]]

    def __init__(self, scripts: list[list[object]]) -> None:
        self._scripts = [list(script) for script in scripts]
        self.converse_calls = 0

    @asynccontextmanager
    async def converse(
        self,
        turn: CaptureTurn,
        tools: Sequence[Tool[CaptureTurn, ToolResult]],
    ) -> AsyncGenerator[AsyncIterator[AgentEvent], None]:
        events = self._events(turn, tools)
        try:
            yield events
        finally:
            await events.aclose()

    async def _events(
        self,
        turn: CaptureTurn,
        tools: Sequence[Tool[CaptureTurn, ToolResult]],
    ) -> AsyncGenerator[AgentEvent, None]:
        _ = turn, tools
        self.converse_calls += 1
        script = self._scripts.pop(0)
        for item in script:
            if item is _RAISE:
                raise RuntimeError("simulated mid-stream failure")
            yield cast(AgentEvent, item)


def _consent_then_draft_agent(draft_script: list[object]) -> "_ScriptedCaptureAgent":
    return _ScriptedCaptureAgent([[DraftingConsentSignalled()], draft_script])


class _OscillatingCaptureAgent:
    converse_calls: int

    def __init__(self) -> None:
        self.converse_calls = 0

    @asynccontextmanager
    async def converse(
        self,
        turn: CaptureTurn,
        tools: Sequence[Tool[CaptureTurn, ToolResult]],
    ) -> AsyncGenerator[AsyncIterator[AgentEvent], None]:
        events = self._events(turn, tools)
        try:
            yield events
        finally:
            await events.aclose()

    async def _events(
        self,
        turn: CaptureTurn,
        tools: Sequence[Tool[CaptureTurn, ToolResult]],
    ) -> AsyncGenerator[AgentEvent, None]:
        _ = turn
        self.converse_calls += 1
        if self.converse_calls > 2:
            raise RuntimeError("opened a third segment")
        names = {tool.name for tool in tools}
        if "signal_drafting_consent" in names:
            yield DraftingConsentSignalled()
            return
        if "request_conversation" in names:
            yield ConversationRequested()
            return
        yield ReplyProduced(text="still here")


def _make_agent_command_stack(capture_agent: object) -> _CommandStack:
    store = InMemoryMessageStore()
    session_repo = InMemoryCaptureSessionRepository()
    message_repo = InMemoryMessageRepository(store)
    uow = _SpyUnitOfWork(session_repo, message_repo, store)
    embedding = DeterministicEmbeddingAdapter()
    factory = cast(Callable[..., GenerateReplyCommand], GenerateReplyCommand)
    command = factory(
        capture_sessions=session_repo,
        uow=uow,
        capture_agent=capture_agent,
        vocabulary=VocabularyResolver(
            embedding, MatchCriteria(threshold=SimilarityScore(value=0.85))
        ),
    )
    return _CommandStack(store, session_repo, message_repo, uow, command)


def _make_command_stack(
    capture_agent: DeterministicCaptureAgentAdapter | None = None,
) -> _CommandStack:
    store = InMemoryMessageStore()
    session_repo = InMemoryCaptureSessionRepository()
    message_repo = InMemoryMessageRepository(store)
    uow = _SpyUnitOfWork(session_repo, message_repo, store)
    embedding = DeterministicEmbeddingAdapter()
    agent = capture_agent or DeterministicCaptureAgentAdapter()
    command = GenerateReplyCommand(
        capture_sessions=session_repo,
        uow=uow,  # pyright: ignore[reportArgumentType]
        capture_agent=agent,
        vocabulary=VocabularyResolver(
            embedding, MatchCriteria(threshold=SimilarityScore(value=0.85))
        ),
    )
    return _CommandStack(store, session_repo, message_repo, uow, command)


class _SpyUnitOfWork(InMemoryUnitOfWork):
    commit_count: int

    def __init__(
        self,
        capture_sessions: InMemoryCaptureSessionRepository,
        messages: InMemoryMessageRepository,
        message_store: InMemoryMessageStore,
        notes: InMemoryNoteRepository | None = None,
        topics: InMemoryTopicRepository | None = None,
        tags: InMemoryTagRepository | None = None,
        outbox_store: InMemoryOutboxStore | None = None,
        outbox: InMemoryOutboxAppender | None = None,
    ) -> None:
        resolved_outbox_store = outbox_store or InMemoryOutboxStore()
        resolved_topics = topics or InMemoryTopicRepository()
        resolved_tags = tags or InMemoryTagRepository()
        super().__init__(
            capture_sessions,
            messages,
            message_store,
            notes or InMemoryNoteRepository(),
            resolved_topics,
            resolved_tags,
            InMemoryNoteVocabularyRepository(resolved_topics, resolved_tags),
            resolved_outbox_store,
            outbox or InMemoryOutboxAppender(resolved_outbox_store),
        )
        self.commit_count = 0

    @override
    async def commit(self) -> None:
        self.commit_count += 1
        await super().commit()
