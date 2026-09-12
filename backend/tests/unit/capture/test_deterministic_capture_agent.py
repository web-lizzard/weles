from collections.abc import Sequence

from adapters.out.in_memory.capture.capture_agent import (
    DeterministicCaptureAgentAdapter,
)
from domain.capture.capture_session import CaptureSession
from domain.capture.deps import NULL_CAPTURE_DEPS
from domain.capture.graph import CaptureMachine
from domain.capture.instructions import HANDOFF
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
from domain.shared.instruction.model import Instruction

_CONFIRMATION = "that's all"

_ADAPTER_AUTHORED_PROSE = (
    "I'll draft a note summarizing our conversation.",
    "what you've said so far",
    "the parts you haven't unpacked yet",
    "You've got a handle on:",
    "Let's dig into:",
)


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
    tools = CaptureMachine(turn, NULL_CAPTURE_DEPS).get_tools()
    for tool in tools:
        if tool.name == name:
            return tool
    raise AssertionError(f"tool {name!r} not offered for this turn")


async def _collect(
    adapter: DeterministicCaptureAgentAdapter,
    turn: CaptureTurn,
    tools: Sequence[Tool[CaptureTurn, ToolResult]],
    instruction: Instruction | None = None,
) -> list[object]:
    machine = CaptureMachine(turn, NULL_CAPTURE_DEPS)
    if instruction is None:
        instruction = machine.current_state.instruction_builder.build(turn)
    async with adapter.converse(turn, tools, instruction) as events:
        return [event async for event in events]


def _handoff_text(instruction: Instruction) -> str:
    for block in instruction.blocks:
        if block.name == HANDOFF:
            return block.text
    raise AssertionError("instruction has no handoff block")


def _reply_text(events: list[object]) -> str:
    return "".join(chunk.text for chunk in events if isinstance(chunk, ReplyProduced))


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
    tools = CaptureMachine(turn, NULL_CAPTURE_DEPS).get_tools()

    events = await _collect(adapter, turn, tools)

    assert any(isinstance(event, NoteTopicProposed) for event in events)
    assert any(isinstance(event, NoteTagProposed) for event in events)
    note_chunks = [event for event in events if isinstance(event, NoteContentProduced)]
    assert note_chunks
    assert "".join(chunk.content.value for chunk in note_chunks).strip() != ""


async def test_drafting_opener_is_handoff_block_text_verbatim() -> None:
    adapter = DeterministicCaptureAgentAdapter()
    turn = _turn(phase=CapturePhase.DRAFTING)
    machine = CaptureMachine(turn, NULL_CAPTURE_DEPS)
    instruction = machine.current_state.instruction_builder.build(turn)
    tools = machine.get_tools()

    events = await _collect(adapter, turn, tools, instruction=instruction)

    assert _reply_text(events) == _handoff_text(instruction)


async def test_conversational_reply_contains_no_adapter_authored_prose() -> None:
    adapter = DeterministicCaptureAgentAdapter()
    turn = _turn()

    events = await _collect(adapter, turn, [])

    reply = _reply_text(events)
    for fragment in _ADAPTER_AUTHORED_PROSE:
        assert fragment not in reply


async def test_drafting_branch_follows_draft_state_block_not_note_tool_names() -> None:
    adapter = DeterministicCaptureAgentAdapter()
    conversing_turn = _turn(phase=CapturePhase.CONVERSING)
    drafting_turn = _turn(phase=CapturePhase.DRAFTING)
    drafting_instruction = CaptureMachine(
        drafting_turn, NULL_CAPTURE_DEPS
    ).current_state.instruction_builder.build(drafting_turn)

    drafting_path_events = await _collect(
        adapter, conversing_turn, [], instruction=drafting_instruction
    )
    assert any(isinstance(event, NoteTopicProposed) for event in drafting_path_events)

    drafting_phase_turn = _turn(phase=CapturePhase.DRAFTING)
    note_tools = CaptureMachine(drafting_phase_turn, NULL_CAPTURE_DEPS).get_tools()
    conversing_instruction = CaptureMachine(
        conversing_turn, NULL_CAPTURE_DEPS
    ).current_state.instruction_builder.build(conversing_turn)

    conversing_path_events = await _collect(
        adapter,
        drafting_phase_turn,
        note_tools,
        instruction=conversing_instruction,
    )
    assert not any(
        isinstance(event, NoteTopicProposed) for event in conversing_path_events
    )
    assert _reply_text(conversing_path_events).strip() != ""
