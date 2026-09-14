import importlib
from collections.abc import AsyncIterator

from pydantic_ai import Agent, models
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from adapters.out.llm.capture import agent as llm_capture_agent_module
from adapters.out.llm.capture.agent import PydanticAiCaptureAgentAdapter
from domain.capture.capture_session import CaptureSession
from domain.capture.deps import NULL_CAPTURE_DEPS
from domain.capture.graph import CaptureMachine, Conversing, Drafting
from domain.capture.instructions import (
    DRAFT_STATE,
    ConversingInstructionBuilder,
    DraftingInstructionBuilder,
)
from domain.capture.message import Message
from domain.capture.turn import CaptureTurn
from domain.capture.value_objects import CapturePhase, MessageContent, MessageRole
from domain.shared.identity.model import UserId

models.ALLOW_MODEL_REQUESTS = False


def _turn(*, phase: CapturePhase = CapturePhase.CONVERSING) -> CaptureTurn:
    session = CaptureSession.start(UserId.new())
    session.phase = phase
    message = Message.record(
        session_id=session.id,
        role=MessageRole.USER,
        content=MessageContent(value="Explain TCP handshakes"),
    )
    return CaptureTurn(session=session, messages=(message,))


def test_conversing_phase_declares_conversing_instruction_builder() -> None:
    builder = Conversing().instruction_builder

    assert isinstance(builder, ConversingInstructionBuilder)


def test_drafting_phase_declares_drafting_instruction_builder() -> None:
    builder = Drafting().instruction_builder

    assert isinstance(builder, DraftingInstructionBuilder)


def test_build_instruction_matches_phase_builder_while_conversing() -> None:
    turn = _turn(phase=CapturePhase.CONVERSING)
    machine = CaptureMachine(turn, NULL_CAPTURE_DEPS)

    built = machine.build_instruction()
    expected = machine.current_state.instruction_builder.build(turn)

    assert built.blocks == expected.blocks
    assert built.required == expected.required


def test_build_instruction_matches_phase_builder_while_drafting() -> None:
    turn = _turn(phase=CapturePhase.DRAFTING)
    machine = CaptureMachine(turn, NULL_CAPTURE_DEPS)

    built = machine.build_instruction()
    expected = machine.current_state.instruction_builder.build(turn)

    assert built.blocks == expected.blocks
    assert DRAFT_STATE in {block.name for block in built.blocks}


class _InstructionCapturingModel(FunctionModel):
    def __init__(self) -> None:
        self.captured_instructions: list[str | None] = []
        super().__init__(
            self._respond,
            stream_function=self._stream,
        )

    async def _respond(
        self, _messages: list[ModelMessage], info: AgentInfo
    ) -> ModelResponse:
        self.captured_instructions.append(info.instructions)
        return ModelResponse(parts=[TextPart("ok")])

    async def _stream(
        self, _messages: list[ModelMessage], info: AgentInfo
    ) -> AsyncIterator[str]:
        self.captured_instructions.append(info.instructions)
        yield "ok"


async def test_pydantic_adapter_forwards_instruction_blocks_to_model() -> None:
    model = _InstructionCapturingModel()
    adapter = PydanticAiCaptureAgentAdapter(Agent(model=model), "test")
    turn = _turn()
    machine = CaptureMachine(turn, NULL_CAPTURE_DEPS)
    instruction = machine.build_instruction()
    expected = "\n".join(block.text for block in instruction.blocks)

    async with adapter.converse(turn, [], instruction) as events:
        _ = [event async for event in events]

    assert model.captured_instructions == [expected]
    legacy_conversing_prose = (
        "Continue this capture conversation with the user. "
        "Stay on their topic and reply in their language."
    )
    assert expected != legacy_conversing_prose


def test_llm_capture_adapter_module_has_no_phase_prose_helpers() -> None:
    module = importlib.reload(llm_capture_agent_module)

    assert not hasattr(module, "_CONVERSING_INSTRUCTIONS")
    assert not hasattr(module, "_DRAFTING_INSTRUCTIONS")
    assert not hasattr(module, "_instructions_for")
