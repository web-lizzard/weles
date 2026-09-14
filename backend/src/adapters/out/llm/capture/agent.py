import inspect
from collections.abc import AsyncGenerator, AsyncIterator, Sequence
from contextlib import asynccontextmanager

from pydantic import BaseModel, ValidationError
from pydantic_ai import (
    Agent,
    AgentRunResultEvent,
    FunctionToolset,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    ToolResultEvent,
)
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.tools import Tool as PydanticAiTool

from adapters.out.llm.tracing import ObservationRecorder, observation
from domain.capture.graph import (
    ConversationRequestSignal,
    CoverageAssessment,
    DraftingConsentSignal,
    NoteContentProposal,
    NoteTagProposal,
    NoteTopicProposal,
    SessionTopicProposal,
)
from domain.capture.message import Message
from domain.capture.turn import (
    AgentEvent,
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
from domain.capture.value_objects import MessageRole
from domain.shared.graph.model import Tool, ToolResult
from domain.shared.instruction.model import Instruction


class PydanticAiCaptureAgentAdapter:
    _agent: Agent
    _model_name: str

    def __init__(self, agent: Agent, model_name: str) -> None:
        self._agent = agent
        self._model_name = model_name

    @asynccontextmanager
    async def converse(
        self,
        turn: CaptureTurn,
        tools: Sequence[Tool[CaptureTurn, ToolResult]],
        instruction: Instruction,
    ) -> AsyncGenerator[AsyncIterator[AgentEvent], None]:
        user_prompt, message_history = _prompt_and_history(turn)
        toolset = FunctionToolset[object](
            tools=[_pydantic_tool(tool, turn) for tool in tools]
        )
        tools_by_name = {tool.name: tool for tool in tools}
        with observation(
            "capture_turn",
            observation_type="agent",
            input_value=_observation_input(turn),
            session_id=str(turn.session.id.value),
        ) as recorder:
            recorder.record_model(self._model_name)
            async with self._agent.run_stream_events(
                user_prompt,
                message_history=message_history,
                instructions=[block.text for block in instruction.blocks],
                toolsets=[toolset],
            ) as raw:
                events = _mapped_events(raw, turn, tools_by_name, recorder)
                try:
                    yield events
                finally:
                    await events.aclose()


async def _mapped_events(
    raw: AsyncIterator[object],
    turn: CaptureTurn,
    tools_by_name: dict[str, Tool[CaptureTurn, ToolResult]],
    recorder: ObservationRecorder,
) -> AsyncGenerator[AgentEvent, None]:
    async for event in raw:
        mapped = _agent_event(event, turn, tools_by_name)
        if mapped is not None:
            yield mapped
        if isinstance(event, AgentRunResultEvent):
            usage = event.result.usage
            recorder.record_usage(
                {
                    "input": usage.input_tokens,
                    "output": usage.output_tokens,
                }
            )


def _prompt_and_history(
    turn: CaptureTurn,
) -> tuple[str | None, list[ModelMessage] | None]:
    remaining = list(turn.messages)
    prompt: str | None = None
    if remaining and remaining[-1].role is MessageRole.USER:
        prompt = remaining[-1].content.value
        remaining = remaining[:-1]
    history = [_model_message(message) for message in remaining]
    return prompt, history or None


def _model_message(message: Message) -> ModelMessage:
    text = message.content.value
    if message.role is MessageRole.USER:
        return ModelRequest(parts=[UserPromptPart(content=text)])
    return ModelResponse(parts=[TextPart(content=text)])


def _observation_input(turn: CaptureTurn) -> list[dict[str, str]]:
    return [
        {"role": message.role.value, "content": message.content.value}
        for message in turn.messages
    ]


def _pydantic_tool(
    tool: Tool[CaptureTurn, ToolResult], turn: CaptureTurn
) -> PydanticAiTool[object]:
    parameter_types = _parameter_types(tool.result)

    async def invoke(**arguments: object) -> ToolResult:
        return await tool.handler(turn, arguments)

    invoke.__name__ = tool.name
    invoke.__qualname__ = tool.name
    invoke.__doc__ = tool.description
    invoke.__annotations__ = {**parameter_types, "return": tool.result}
    invoke.__signature__ = inspect.Signature(  # pyright: ignore[reportFunctionMemberAccess]
        [
            inspect.Parameter(
                name,
                inspect.Parameter.KEYWORD_ONLY,
                annotation=annotation,
            )
            for name, annotation in parameter_types.items()
        ],
        return_annotation=tool.result,
    )
    return PydanticAiTool(
        invoke,
        name=tool.name,
        description=tool.description,
        takes_ctx=False,
    )


def _parameter_types(result_type: type[ToolResult]) -> dict[str, type[object]]:
    parameters: dict[str, type[object]] = {}
    for name, field in result_type.model_fields.items():
        if name == "tool":
            continue
        annotation: object = field.annotation
        parameters[name] = _argument_type(annotation)
    return parameters


def _argument_type(annotation: object) -> type[object]:
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        value_field = annotation.model_fields.get("value")
        if value_field is not None and len(annotation.model_fields) == 1:
            inner: object = value_field.annotation
            if isinstance(inner, type):
                return inner
    if isinstance(annotation, type):
        return annotation
    return object


def _agent_event(
    event: object,
    turn: CaptureTurn,
    tools_by_name: dict[str, Tool[CaptureTurn, ToolResult]],
) -> AgentEvent | None:
    if isinstance(event, PartStartEvent) and isinstance(event.part, TextPart):
        return _text_event(turn, event.part.content)
    if isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
        return _text_event(turn, event.delta.content_delta)
    if isinstance(event, ToolResultEvent) and isinstance(event.part, ToolReturnPart):
        domain_tool = tools_by_name.get(event.part.tool_name)
        if domain_tool is None:
            return None
        result = _parse_tool_result(event.part.content, domain_tool.result)
        if result is None:
            return None
        return _event_from_tool_result(result, turn)
    return None


def _text_event(_turn: CaptureTurn, text: str) -> AgentEvent | None:
    if not text:
        return None
    return ReplyProduced(text=text)


def _parse_tool_result(
    content: object, result_type: type[ToolResult]
) -> ToolResult | None:
    if isinstance(content, result_type):
        return content
    try:
        return result_type.model_validate(content)
    except ValidationError:
        return None


def _event_from_tool_result(result: ToolResult, turn: CaptureTurn) -> AgentEvent | None:
    if isinstance(result, SessionTopicProposal):
        return SessionTopicProposed(topic=result.topic)
    if isinstance(result, NoteTopicProposal):
        return NoteTopicProposed(label=result.label)
    if isinstance(result, NoteTagProposal):
        if turn.draft is None or turn.draft.topic is None:
            return None
        return NoteTagProposed(label=result.label)
    if isinstance(result, NoteContentProposal):
        if turn.draft is None or turn.draft.topic is None:
            return ReplyProduced(text=result.content.value)
        return NoteContentProduced(content=result.content)
    if isinstance(result, DraftingConsentSignal):
        return DraftingConsentSignalled()
    if isinstance(result, ConversationRequestSignal):
        return ConversationRequested()
    if isinstance(result, CoverageAssessment):
        return CoverageAssessed(coverage=result.coverage)
    return None
