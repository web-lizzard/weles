from collections.abc import Callable, Sequence
from typing import cast

import pytest
from pydantic_ai import Agent, models
from pydantic_ai.models.test import TestModel

from adapters.out.in_memory.capture.capture_agent import (
    DeterministicCaptureAgentAdapter,
)
from adapters.out.llm.capture.agent import PydanticAiCaptureAgentAdapter
from domain.capture.capture_session import CaptureSession
from domain.capture.deps import NULL_CAPTURE_DEPS
from domain.capture.graph import CaptureMachine
from domain.capture.instructions import DRAFT_STATE
from domain.capture.message import Message
from domain.capture.ports import CaptureAgentPort
from domain.capture.turn import (
    AssistantMessageRecorded,
    CaptureTurn,
    ReplyProduced,
    UserMessageRecorded,
)
from domain.capture.value_objects import (
    CapturePhase,
    MessageContent,
    MessageRole,
    SessionTopic,
)
from domain.shared.graph.model import Tool, ToolResult
from domain.shared.identity.model import UserId
from domain.shared.instruction.model import Instruction

models.ALLOW_MODEL_REQUESTS = False

_OWNER = UserId.new()


def _make_pydantic_capture_agent() -> CaptureAgentPort:
    agent = Agent(model=TestModel())
    return cast(
        CaptureAgentPort,
        cast(object, PydanticAiCaptureAgentAdapter(agent, "test")),
    )


def _make_deterministic_capture_agent() -> CaptureAgentPort:
    return cast(
        CaptureAgentPort,
        cast(object, DeterministicCaptureAgentAdapter()),
    )


_IMPLEMENTATIONS: list[Callable[[], CaptureAgentPort]] = [
    _make_pydantic_capture_agent,
    _make_deterministic_capture_agent,
]


def _conversing_turn() -> CaptureTurn:
    session = CaptureSession.start(_OWNER)
    session.phase = CapturePhase.CONVERSING
    message = Message.record(
        session_id=session.id,
        role=MessageRole.USER,
        content=MessageContent(value="Explain TCP handshakes"),
    )
    return CaptureTurn(session=session, messages=(message,))


def _drafting_turn() -> CaptureTurn:
    session = CaptureSession.start(_OWNER)
    session.phase = CapturePhase.DRAFTING
    session.assign_topic(SessionTopic(value="TCP handshakes"))
    message = Message.record(
        session_id=session.id,
        role=MessageRole.USER,
        content=MessageContent(value="that's all"),
    )
    return CaptureTurn(session=session, messages=(message,))


def _instruction_for_turn(turn: CaptureTurn) -> Instruction:
    machine = CaptureMachine(turn, NULL_CAPTURE_DEPS)
    return machine.build_instruction()


async def _collect(
    adapter: CaptureAgentPort,
    turn: CaptureTurn,
    tools: Sequence[Tool[CaptureTurn, ToolResult]],
) -> list[object]:
    instruction = _instruction_for_turn(turn)
    async with adapter.converse(turn, tools, instruction) as events:
        return [event async for event in events]


@pytest.mark.parametrize(
    "make_adapter", _IMPLEMENTATIONS, ids=["pydantic_ai", "deterministic"]
)
async def test_converse_yields_only_agent_events_not_command_recording_events(
    make_adapter: Callable[[], CaptureAgentPort],
) -> None:
    adapter = make_adapter()
    events = await _collect(adapter, _conversing_turn(), [])

    assert events
    assert not any(isinstance(event, UserMessageRecorded) for event in events)
    assert not any(isinstance(event, AssistantMessageRecorded) for event in events)


@pytest.mark.parametrize(
    "make_adapter", _IMPLEMENTATIONS, ids=["pydantic_ai", "deterministic"]
)
async def test_converse_yields_joinable_reply_produced_while_conversing(
    make_adapter: Callable[[], CaptureAgentPort],
) -> None:
    adapter = make_adapter()
    events = await _collect(adapter, _conversing_turn(), [])

    reply_chunks = [event for event in events if isinstance(event, ReplyProduced)]
    assert reply_chunks
    assert "".join(chunk.text for chunk in reply_chunks).strip() != ""


@pytest.mark.parametrize(
    "make_adapter", _IMPLEMENTATIONS, ids=["pydantic_ai", "deterministic"]
)
async def test_converse_accepts_instruction_built_for_the_turns_drafting_phase(
    make_adapter: Callable[[], CaptureAgentPort],
) -> None:
    adapter = make_adapter()
    turn = _drafting_turn()
    instruction = _instruction_for_turn(turn)
    block_names = {block.name for block in instruction.blocks}

    assert DRAFT_STATE in block_names

    events = await _collect(adapter, turn, [])

    assert events
