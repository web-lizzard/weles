from typing import override
from uuid import uuid4

import pytest

from domain.capture.capture_session import CaptureSession
from domain.capture.instructions import (
    COVERAGE_TREND,
    DRAFT_STATE,
    FLOW,
    HANDOFF,
    LANGUAGE,
    SESSION_TOPIC,
    TASK,
    ConversingInstructionBuilder,
    DraftingInstructionBuilder,
)
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.turn import CaptureTurn, NoteDraft
from domain.capture.value_objects import (
    Coverage,
    Embedding,
    Label,
    NoteId,
    SessionTopic,
)
from domain.shared.identity.model import UserId
from domain.shared.instruction.model import Instruction, InstructionBlock

_EMBEDDING_MODEL = "test"
_OWNER = UserId.new()


def _turn(
    *,
    session: CaptureSession | None = None,
    draft: NoteDraft | None = None,
) -> CaptureTurn:
    return CaptureTurn(
        session=session or CaptureSession.start(_OWNER),
        messages=(),
        draft=draft,
    )


def _block_names(instruction: Instruction) -> tuple[str, ...]:
    return tuple(block.name for block in instruction.blocks)


def test_conversing_instruction_leads_with_flow_and_language_then_task() -> None:
    builder = ConversingInstructionBuilder()
    instruction = builder.build(_turn())

    assert _block_names(instruction) == (FLOW, LANGUAGE, TASK)
    assert builder.required == instruction.required
    assert builder.required == frozenset({FLOW, LANGUAGE, TASK})


@pytest.mark.parametrize(
    ("has_topic", "has_assessment", "expected_tail"),
    [
        (False, False, ()),
        (True, False, (SESSION_TOPIC,)),
        (False, True, (COVERAGE_TREND,)),
        (True, True, (SESSION_TOPIC, COVERAGE_TREND)),
    ],
)
def test_conversing_instruction_adds_optional_blocks_only_when_context_supports_them(
    has_topic: bool,
    has_assessment: bool,
    expected_tail: tuple[str, ...],
) -> None:
    session = CaptureSession.start(_OWNER)
    if has_topic:
        session.assign_topic(SessionTopic(value="billing"))
    if has_assessment:
        session.record_assessment(Coverage(value=0.3))

    instruction = ConversingInstructionBuilder().build(_turn(session=session))

    assert _block_names(instruction) == (FLOW, LANGUAGE, TASK, *expected_tail)
    if SESSION_TOPIC in expected_tail:
        topic_block = next(
            block for block in instruction.blocks if block.name == SESSION_TOPIC
        )
        assert "billing" in topic_block.text
    if COVERAGE_TREND in expected_tail:
        trend_block = next(
            block for block in instruction.blocks if block.name == COVERAGE_TREND
        )
        assert trend_block.text


def test_drafting_first_pass_includes_empty_draft_state_and_handoff() -> None:
    builder = DraftingInstructionBuilder()
    instruction = builder.build(_turn())

    assert _block_names(instruction) == (
        FLOW,
        LANGUAGE,
        TASK,
        DRAFT_STATE,
        HANDOFF,
    )
    assert builder.required == instruction.required
    assert builder.required == frozenset({FLOW, LANGUAGE, TASK, DRAFT_STATE})
    draft_state = next(
        block for block in instruction.blocks if block.name == DRAFT_STATE
    )
    assert "Nothing of the note exists yet" in draft_state.text


def test_drafting_uses_revising_state_when_note_exists_without_draft() -> None:
    session = CaptureSession.start(_OWNER)
    session.assign_topic(SessionTopic(value="TCP handshakes"))
    session.note_id = NoteId(value=uuid4())

    instruction = DraftingInstructionBuilder().build(_turn(session=session))

    assert HANDOFF not in _block_names(instruction)
    draft_state = next(
        block for block in instruction.blocks if block.name == DRAFT_STATE
    )
    assert "revising" in draft_state.text.lower()
    assert "TCP handshakes" in draft_state.text


def test_drafting_instruction_uses_underway_draft_state_when_draft_is_in_hand() -> None:
    topic = Topic.mint(
        _OWNER,
        Label(value="latency"),
        Embedding(model=_EMBEDDING_MODEL, values=(0.1, 0.2)),
    )
    tag = Tag.mint(
        _OWNER,
        Label(value="networking"),
        Embedding(model=_EMBEDDING_MODEL, values=(0.3, 0.4)),
    )
    draft = NoteDraft(topic=topic, tags=[tag], content="Some body.")

    instruction = DraftingInstructionBuilder().build(_turn(draft=draft))

    assert HANDOFF not in _block_names(instruction)
    draft_state = next(
        block for block in instruction.blocks if block.name == DRAFT_STATE
    )
    assert "latency" in draft_state.text
    assert "networking" in draft_state.text


class _TasklessConversingBuilder(ConversingInstructionBuilder):
    @override
    def phase_blocks(self, context: CaptureTurn) -> tuple[InstructionBlock, ...]:
        return ()


def test_build_raises_when_phase_withholds_a_required_block() -> None:
    with pytest.raises(ValueError, match="missing required blocks"):
        _ = _TasklessConversingBuilder().build(_turn())
