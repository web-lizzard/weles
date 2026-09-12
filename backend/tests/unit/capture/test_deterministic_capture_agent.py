from collections.abc import Sequence

from adapters.out.in_memory.capture.capture_agent import (
    DeterministicCaptureAgentAdapter,
)
from domain.capture.capture_session import CaptureSession
from domain.capture.graph import CaptureMachine
from domain.capture.message import Message
from domain.capture.turn import (
    CaptureTurn,
    DraftingConsentSignalled,
    NoteContentProduced,
    NoteTagProposed,
    NoteTopicProposed,
    ReplyProduced,
)
from domain.capture.value_objects import (
    CapturePhase,
    MessageContent,
    MessageRole,
)
from domain.shared.graph.model import Tool, ToolResult

_CONFIRMATION = "that's all"


def _turn(
    *,
    phase: CapturePhase = CapturePhase.CONVERSING,
    messages: Sequence[Message] | None = None,
) -> CaptureTurn:
    session = CaptureSession.start()
    session.phase = phase
    if messages is None:
        messages = (
            Message.record(
                session_id=session.id,
                role=MessageRole.USER,
                content=MessageContent(value="Explain TCP handshakes"),
            ),
        )
    return CaptureTurn(session=session, messages=messages)


def _drafting_confirmation_turn() -> CaptureTurn:
    session = CaptureSession.start()
    session.phase = CapturePhase.CONVERSING
    messages = (
        Message.record(
            session_id=session.id,
            role=MessageRole.USER,
            content=MessageContent(value="Let's talk through TCP handshakes"),
        ),
        Message.record(
            session_id=session.id,
            role=MessageRole.AGENT,
            content=MessageContent(value="What do you know about the SYN packet?"),
        ),
        Message.record(
            session_id=session.id,
            role=MessageRole.USER,
            content=MessageContent(value=_CONFIRMATION),
        ),
    )
    return CaptureTurn(session=session, messages=messages)


def _tool_named(turn: CaptureTurn, name: str) -> Tool[CaptureTurn, ToolResult]:
    tools = CaptureMachine(turn).get_tools()
    for tool in tools:
        if tool.name == name:
            return tool
    raise AssertionError(f"tool {name!r} not offered for this turn")


async def _collect(
    adapter: DeterministicCaptureAgentAdapter,
    turn: CaptureTurn,
    tools: Sequence[Tool[CaptureTurn, ToolResult]],
) -> list[object]:
    return [event async for event in adapter.converse(turn, tools)]


async def test_conversing_yields_chunked_reply_produced() -> None:
    adapter = DeterministicCaptureAgentAdapter()
    turn = _turn()

    events = await _collect(adapter, turn, [])

    reply_chunks = [event for event in events if isinstance(event, ReplyProduced)]
    assert reply_chunks
    assert "".join(chunk.text for chunk in reply_chunks).strip() != ""


async def test_confirmation_yields_drafting_consent_signalled_when_tool_offered() -> (
    None
):
    adapter = DeterministicCaptureAgentAdapter()
    turn = _drafting_confirmation_turn()

    events = await _collect(
        adapter, turn, [_tool_named(turn, "signal_drafting_consent")]
    )

    assert events == [DraftingConsentSignalled()]


async def test_drafting_tools_yield_topic_tags_and_chunked_note_content() -> None:
    adapter = DeterministicCaptureAgentAdapter()
    turn = _turn(phase=CapturePhase.DRAFTING)
    tools = CaptureMachine(turn).get_tools()

    events = await _collect(adapter, turn, tools)

    assert any(isinstance(event, NoteTopicProposed) for event in events)
    assert any(isinstance(event, NoteTagProposed) for event in events)
    note_chunks = [event for event in events if isinstance(event, NoteContentProduced)]
    assert note_chunks
    assert "".join(chunk.content.value for chunk in note_chunks).strip() != ""
