import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.trace import StatusCode
from pydantic_ai import Agent, models
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from adapters.out.llm.distill.structured_task import PydanticAiStructuredTaskAdapter
from adapters.out.llm.tracing import OBSERVATION_MODEL_NAME, OBSERVATION_USAGE_DETAILS
from domain.distill.card_factory import CardFactory
from domain.distill.instructions import (
    GeneratingInstructionBuilder,
    MergingInstructionBuilder,
    ReviewingInstructionBuilder,
)
from domain.distill.note import mint_note
from domain.distill.note_document import NoteDocument
from domain.distill.regeneration import RegenerationPolicy, ThresholdTier
from domain.distill.run import (
    CandidateRound,
    CardsProposed,
    CardsReviewed,
    DistillRun,
    DuplicatesFound,
)
from domain.distill.value_objects import (
    CardLengthPolicy,
    CardProposal,
    NoteContent,
    NoteId,
    SessionId,
    TopicSnapshot,
)

models.ALLOW_MODEL_REQUESTS = False

_CONTENT = "Connections are established via a three-way handshake."


def _install_in_memory_tracer() -> InMemorySpanExporter:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return exporter


def _policy() -> RegenerationPolicy:
    return RegenerationPolicy(
        tiers=(
            ThresholdTier(max_length=1500, min_accepted_share=0.5),
            ThresholdTier(max_length=6000, min_accepted_share=0.6),
            ThresholdTier(max_length=None, min_accepted_share=0.7),
        )
    )


def _run(content: str = _CONTENT) -> DistillRun:
    note = mint_note(
        NoteId(value=uuid4()),
        SessionId(value=uuid4()),
        TopicSnapshot(id=uuid4(), label="TCP handshakes"),
        NoteContent(value=content),
        [],
        datetime.now(UTC),
    )
    return DistillRun(
        note=note,
        document=NoteDocument.of(note.content),
        policy=_policy(),
    )


def _card_factory() -> CardFactory:
    return CardFactory(CardLengthPolicy(front_max=200, back_max=200))


def _run_with_first_round() -> DistillRun:
    run = _run()
    run.add_round(
        CandidateRound.FIRST,
        [CardProposal(front="Q1", back="A1", quote=_CONTENT)],
        _card_factory(),
    )
    return run


def _adapter(
    model: TestModel | FunctionModel, *, model_name: str = "test"
) -> PydanticAiStructuredTaskAdapter:
    return PydanticAiStructuredTaskAdapter(Agent(model=model), model_name)


class _BoomError(Exception):
    pass


async def test_a_generation_result_is_returned_as_the_requested_output_type() -> None:
    _ = _install_in_memory_tracer()
    adapter = _adapter(TestModel())
    instruction = GeneratingInstructionBuilder().build(_run())

    proposed = await adapter.complete(instruction, CardsProposed)

    assert isinstance(proposed, CardsProposed)


async def test_a_review_result_is_returned_as_the_requested_output_type() -> None:
    _ = _install_in_memory_tracer()
    adapter = _adapter(TestModel())
    instruction = ReviewingInstructionBuilder(CandidateRound.FIRST).build(
        _run_with_first_round()
    )

    reviewed = await adapter.complete(instruction, CardsReviewed)

    assert isinstance(reviewed, CardsReviewed)


async def test_a_merge_result_is_returned_as_the_requested_output_type() -> None:
    _ = _install_in_memory_tracer()
    adapter = _adapter(TestModel())
    instruction = MergingInstructionBuilder().build(_run())

    duplicates = await adapter.complete(instruction, DuplicatesFound)

    assert isinstance(duplicates, DuplicatesFound)


async def test_instruction_block_texts_reach_the_model_as_instructions() -> None:
    _ = _install_in_memory_tracer()
    captured: list[ModelMessage] = []

    def fn(messages: list[ModelMessage], _info: AgentInfo) -> ModelResponse:
        captured.extend(messages)
        return ModelResponse(
            parts=[ToolCallPart(tool_name="final_result", args={"proposals": []})]
        )

    adapter = _adapter(FunctionModel(fn))
    instruction = GeneratingInstructionBuilder().build(_run())

    _ = await adapter.complete(instruction, CardsProposed)

    last = captured[-1]
    assert isinstance(last, ModelRequest)
    sent = last.instructions
    assert sent is not None
    for block in instruction.blocks:
        assert block.text in sent


async def test_the_span_is_named_from_the_output_with_model_and_usage_recorded() -> (
    None
):
    exporter = _install_in_memory_tracer()
    model_name = "openai/gpt-4o-mini"
    adapter = _adapter(TestModel(), model_name=model_name)
    instruction = GeneratingInstructionBuilder().build(_run())

    _ = await adapter.complete(instruction, CardsProposed)

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "cards_proposed"
    attributes = span.attributes
    assert attributes is not None
    assert attributes[OBSERVATION_MODEL_NAME] == model_name
    usage = attributes[OBSERVATION_USAGE_DETAILS]
    assert isinstance(usage, str)
    assert json.loads(usage)["input"] > 0
    assert json.loads(usage)["output"] > 0


async def test_review_and_merge_spans_are_also_named_from_their_output() -> None:
    exporter = _install_in_memory_tracer()
    adapter = _adapter(TestModel())
    review_instruction = ReviewingInstructionBuilder(CandidateRound.FIRST).build(
        _run_with_first_round()
    )
    merge_instruction = MergingInstructionBuilder().build(_run())

    _ = await adapter.complete(review_instruction, CardsReviewed)
    _ = await adapter.complete(merge_instruction, DuplicatesFound)

    names = [span.name for span in exporter.get_finished_spans()]
    assert names == ["cards_reviewed", "duplicates_found"]


async def test_a_model_error_propagates_and_marks_the_span_errored() -> None:
    exporter = _install_in_memory_tracer()

    def fn(_messages: list[ModelMessage], _info: AgentInfo) -> ModelResponse:
        raise _BoomError("model exploded")

    adapter = _adapter(FunctionModel(fn))
    instruction = GeneratingInstructionBuilder().build(_run())

    with pytest.raises(_BoomError):
        _ = await adapter.complete(instruction, CardsProposed)

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].status.status_code == StatusCode.ERROR
