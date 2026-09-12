from collections.abc import Callable, Sequence
from typing import cast

import pytest
from pydantic_ai import Agent, models
from pydantic_ai.models.test import TestModel

from adapters.out.llm.capture.agent import PydanticAiCaptureAgentAdapter
from domain.capture.capture_session import CaptureSession
from domain.capture.message import Message
from domain.capture.ports import CaptureAgentPort
from domain.capture.turn import (
    AssistantMessageRecorded,
    CaptureTurn,
    ReplyProduced,
    UserMessageRecorded,
)
from domain.capture.value_objects import CapturePhase, MessageContent, MessageRole
from domain.shared.graph.model import Tool, ToolResult

models.ALLOW_MODEL_REQUESTS = False


def _make_pydantic_capture_agent() -> CaptureAgentPort:
    agent = Agent(model=TestModel())
    return cast(
        CaptureAgentPort,
        cast(object, PydanticAiCaptureAgentAdapter(agent, "test")),
    )


_IMPLEMENTATIONS: list[Callable[[], CaptureAgentPort]] = [
    _make_pydantic_capture_agent,
]


def _conversing_turn() -> CaptureTurn:
    session = CaptureSession.start()
    session.phase = CapturePhase.CONVERSING
    message = Message.record(
        session_id=session.id,
        role=MessageRole.USER,
        content=MessageContent(value="Explain TCP handshakes"),
    )
    return CaptureTurn(session=session, messages=(message,))


async def _collect(
    adapter: CaptureAgentPort,
    turn: CaptureTurn,
    tools: Sequence[Tool[CaptureTurn, ToolResult]],
) -> list[object]:
    return [event async for event in adapter.converse(turn, tools)]


@pytest.mark.parametrize("make_adapter", _IMPLEMENTATIONS, ids=["pydantic_ai"])
async def test_converse_yields_only_agent_events_not_command_recording_events(
    make_adapter: Callable[[], CaptureAgentPort],
) -> None:
    adapter = make_adapter()
    events = await _collect(adapter, _conversing_turn(), [])

    assert events
    assert not any(isinstance(event, UserMessageRecorded) for event in events)
    assert not any(isinstance(event, AssistantMessageRecorded) for event in events)


@pytest.mark.parametrize("make_adapter", _IMPLEMENTATIONS, ids=["pydantic_ai"])
async def test_converse_yields_joinable_reply_produced_while_conversing(
    make_adapter: Callable[[], CaptureAgentPort],
) -> None:
    adapter = make_adapter()
    events = await _collect(adapter, _conversing_turn(), [])

    reply_chunks = [event for event in events if isinstance(event, ReplyProduced)]
    assert reply_chunks
    assert "".join(chunk.text for chunk in reply_chunks).strip() != ""
