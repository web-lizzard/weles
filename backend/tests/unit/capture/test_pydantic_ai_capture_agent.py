import json
from collections.abc import AsyncIterator, Sequence
from typing import override

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from pydantic_ai import Agent, ModelMessage, ModelResponse, TextPart, models
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from adapters.out.llm.capture.agent import PydanticAiCaptureAgentAdapter
from adapters.out.llm.tracing import (
    OBSERVATION_MODEL_NAME,
    OBSERVATION_TYPE,
    SESSION_ID,
)
from domain.capture.capture_session import CaptureSession
from domain.capture.deps import NULL_CAPTURE_DEPS
from domain.capture.graph import CaptureMachine
from domain.capture.message import Message
from domain.capture.turn import (
    CaptureTurn,
    ConversationRequested,
    CoverageAssessed,
    DraftingConsentSignalled,
    NoteContentProduced,
    NoteTagProposed,
    NoteTopicProposed,
    ReplyProduced,
    SessionTopicProposed,
)
from domain.capture.value_objects import (
    CapturePhase,
    Label,
    MessageContent,
    MessageRole,
    NoteContent,
    SessionTopic,
)
from domain.shared.graph.model import Tool, ToolResult

models.ALLOW_MODEL_REQUESTS = False


def _install_in_memory_tracer() -> InMemorySpanExporter:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return exporter


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


def _adapter(
    model: TestModel | FunctionModel, *, model_name: str = "test"
) -> PydanticAiCaptureAgentAdapter:
    return PydanticAiCaptureAgentAdapter(Agent(model=model), model_name)


async def _collect(
    adapter: PydanticAiCaptureAgentAdapter,
    turn: CaptureTurn,
    tools: Sequence[Tool[CaptureTurn, ToolResult]],
) -> list[object]:
    machine = CaptureMachine(turn, NULL_CAPTURE_DEPS)
    instruction = machine.current_state.instruction_builder.build(turn)
    async with adapter.converse(turn, tools, instruction) as events:
        return [event async for event in events]


def _tool_named(turn: CaptureTurn, name: str) -> Tool[CaptureTurn, ToolResult]:
    tools = CaptureMachine(turn, NULL_CAPTURE_DEPS).get_tools()
    for tool in tools:
        if tool.name == name:
            return tool
    raise AssertionError(f"tool {name!r} not offered for this turn")


async def test_drafting_text_deltas_map_to_note_content_produced() -> None:
    _ = _install_in_memory_tracer()
    adapter = _adapter(TestModel())
    turn = _turn(phase=CapturePhase.DRAFTING)

    events = await _collect(adapter, turn, [])

    note_chunks = [event for event in events if isinstance(event, NoteContentProduced)]
    assert note_chunks
    assert "".join(chunk.content.value for chunk in note_chunks).strip() != ""


async def test_propose_session_topic_tool_maps_to_session_topic_proposed() -> None:
    _ = _install_in_memory_tracer()
    adapter = _adapter(TestModel())
    turn = _turn()

    events = await _collect(adapter, turn, [_tool_named(turn, "propose_session_topic")])

    proposed = [event for event in events if isinstance(event, SessionTopicProposed)]
    assert len(proposed) == 1
    assert proposed[0].topic == SessionTopic(value="a")


async def test_signal_drafting_consent_tool_maps_to_drafting_consent_signalled() -> (
    None
):
    _ = _install_in_memory_tracer()
    adapter = _adapter(TestModel())
    turn = _turn()

    events = await _collect(
        adapter, turn, [_tool_named(turn, "signal_drafting_consent")]
    )

    assert any(isinstance(event, DraftingConsentSignalled) for event in events)


async def test_assess_coverage_tool_maps_to_coverage_assessed() -> None:
    _ = _install_in_memory_tracer()
    adapter = _adapter(TestModel())
    turn = _turn()

    events = await _collect(adapter, turn, [_tool_named(turn, "assess_coverage")])

    assert any(isinstance(event, CoverageAssessed) for event in events)


async def test_propose_note_topic_tool_maps_to_note_topic_proposed() -> None:
    _ = _install_in_memory_tracer()
    adapter = _adapter(TestModel())
    turn = _turn(phase=CapturePhase.DRAFTING)

    events = await _collect(adapter, turn, [_tool_named(turn, "propose_note_topic")])

    proposed = [event for event in events if isinstance(event, NoteTopicProposed)]
    assert len(proposed) == 1
    assert proposed[0].label == Label(value="a")


async def test_propose_note_tag_tool_maps_to_note_tag_proposed() -> None:
    _ = _install_in_memory_tracer()
    adapter = _adapter(TestModel())
    turn = _turn(phase=CapturePhase.DRAFTING)

    events = await _collect(adapter, turn, [_tool_named(turn, "propose_note_tag")])

    proposed = [event for event in events if isinstance(event, NoteTagProposed)]
    assert len(proposed) == 1
    assert proposed[0].label == Label(value="a")


async def test_propose_note_content_tool_maps_to_note_content_produced() -> None:
    _ = _install_in_memory_tracer()
    adapter = _adapter(TestModel())
    turn = _turn(phase=CapturePhase.DRAFTING)

    events = await _collect(adapter, turn, [_tool_named(turn, "propose_note_content")])

    produced = [
        event
        for event in events
        if isinstance(event, NoteContentProduced)
        and event.content == NoteContent(value="a")
    ]
    assert len(produced) == 1


async def test_request_conversation_tool_maps_to_conversation_requested() -> None:
    _ = _install_in_memory_tracer()
    adapter = _adapter(TestModel())
    turn = _turn(phase=CapturePhase.DRAFTING)

    events = await _collect(adapter, turn, [_tool_named(turn, "request_conversation")])

    assert any(isinstance(event, ConversationRequested) for event in events)


async def _function_model_stream(
    _messages: list[ModelMessage], _info: AgentInfo
) -> AsyncIterator[str]:
    yield "streamed "
    yield "reply"


async def _function_model_response(
    _messages: list[ModelMessage], _info: AgentInfo
) -> ModelResponse:
    return ModelResponse(parts=[TextPart("fallback")])


class _StreamingFunctionModel(FunctionModel):
    @override
    def __init__(self) -> None:
        super().__init__(
            _function_model_response,
            stream_function=_function_model_stream,
        )


async def test_function_model_stream_maps_text_deltas_to_reply_produced() -> None:
    _ = _install_in_memory_tracer()
    adapter = _adapter(_StreamingFunctionModel())
    turn = _turn()

    events = await _collect(adapter, turn, [])

    reply_chunks = [event for event in events if isinstance(event, ReplyProduced)]
    assert reply_chunks
    assert "".join(chunk.text for chunk in reply_chunks) == "streamed reply"


async def test_converse_exports_capture_turn_observation_grouped_by_session_id() -> (
    None
):
    exporter = _install_in_memory_tracer()
    model_name = "openai:gpt-4o-mini"
    turn = _turn()
    adapter = _adapter(TestModel(), model_name=model_name)

    _ = await _collect(adapter, turn, [])

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "capture_turn"
    attributes = span.attributes
    assert attributes is not None
    assert attributes[OBSERVATION_TYPE] == "agent"
    assert attributes[OBSERVATION_MODEL_NAME] == model_name
    assert attributes[SESSION_ID] == str(turn.session.id.value)
    observation_input = attributes["langfuse.observation.input"]
    assert isinstance(observation_input, str)
    assert json.loads(observation_input)
