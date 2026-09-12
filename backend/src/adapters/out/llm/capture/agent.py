from collections.abc import AsyncIterator, Sequence
from typing import override

from pydantic_ai import Agent

from domain.capture.turn import AgentEvent, CaptureTurn
from domain.shared.graph.model import Tool, ToolResult


class _EmptyAgentEvents(AsyncIterator[AgentEvent]):
    @override
    def __aiter__(self) -> AsyncIterator[AgentEvent]:
        return self

    @override
    async def __anext__(self) -> AgentEvent:
        raise StopAsyncIteration


class PydanticAiCaptureAgentAdapter:
    _agent: Agent
    _model_name: str

    def __init__(self, agent: Agent, model_name: str) -> None:
        self._agent = agent
        self._model_name = model_name

    def converse(
        self,
        _turn: CaptureTurn,
        _tools: Sequence[Tool[CaptureTurn, ToolResult]],
    ) -> AsyncIterator[AgentEvent]:
        return _EmptyAgentEvents()
