"""Step definitions for coverage wrap-up acceptance scenarios."""

from collections.abc import AsyncGenerator, AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import cast

from bdd.steps.capture import CaptureFlowContext
from integration.support.in_memory_capture import (
    InMemoryCaptureComposition,
)
from pytest_bdd import given, then

from adapters.out.in_memory.capture.capture_agent import (
    DeterministicCaptureAgentAdapter,
)
from domain.capture.turn import AgentEvent, CaptureTurn
from domain.shared.graph.model import Tool, ToolResult
from domain.shared.instruction.model import Instruction


class _FullCoverageCaptureAgent(DeterministicCaptureAgentAdapter):
    @asynccontextmanager
    async def converse(
        self,
        turn: CaptureTurn,
        tools: Sequence[Tool[CaptureTurn, ToolResult]],
        instruction: Instruction,
    ) -> AsyncGenerator[AsyncIterator[AgentEvent], None]:
        async with super().converse(turn, tools, instruction) as events:

            async def with_full_coverage() -> AsyncGenerator[AgentEvent, None]:
                async for event in events:
                    yield event
                turn.coverage_confidence = 1.0

            yield with_full_coverage()


@given("the confidence assessment reports full coverage")
def confidence_assessment_reports_full_coverage(
    capture_composition: InMemoryCaptureComposition,
) -> None:
    capture_composition.capture_agent = cast(
        DeterministicCaptureAgentAdapter,
        cast(object, _FullCoverageCaptureAgent()),
    )


@then("the done event coverage confidence is fully covered")
def done_event_coverage_is_fully_covered(
    capture_flow_context: CaptureFlowContext,
) -> None:
    done_events = [
        event for event in capture_flow_context.reply_events if event["type"] == "done"
    ]
    assert done_events, "expected a done event"
    coverage = done_events[-1]["coverage_confidence"]
    assert isinstance(coverage, (int, float))
    assert coverage >= 1


@then("the follow-up message succeeds with a done event")
def follow_up_message_succeeds_with_done_event(
    capture_flow_context: CaptureFlowContext,
) -> None:
    done_events = [
        event for event in capture_flow_context.reply_events if event["type"] == "done"
    ]
    assert done_events, "expected a done event"
    last_done = done_events[-1]
    assert str(last_done.get("content", "")) != ""
