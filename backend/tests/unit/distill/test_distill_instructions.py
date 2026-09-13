from datetime import UTC, datetime
from uuid import uuid4

import pytest

from domain.distill.card_factory import CardFactory
from domain.distill.instructions import (
    ACCEPTED_EXAMPLE,
    CANDIDATES,
    FLOW,
    GAPS,
    LANGUAGE,
    NOTE,
    TASK,
    GeneratingInstructionBuilder,
    MergingInstructionBuilder,
    RegeneratingInstructionBuilder,
    ReviewingInstructionBuilder,
)
from domain.distill.note import mint_note
from domain.distill.note_document import NoteDocument
from domain.distill.regeneration import RegenerationPolicy, ThresholdTier
from domain.distill.run import Candidate, CandidateRound, DistillRun
from domain.distill.value_objects import (
    CardLengthPolicy,
    CardProposal,
    CardVerdict,
    NoteContent,
    NoteId,
    ReviewGrade,
    SessionId,
    TopicSnapshot,
)
from domain.shared.instruction.model import Instruction

_CONTENT = "Connections are established via a three-way handshake."


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


def _block_names(instruction: Instruction) -> tuple[str, ...]:
    return tuple(block.name for block in instruction.blocks)


def _block_text(instruction: Instruction, name: str) -> str:
    return next(block.text for block in instruction.blocks if block.name == name)


def _reviewed(
    run: DistillRun, round: CandidateRound, grades: list[ReviewGrade]
) -> list[Candidate]:
    """Add one proposal per grade to `round` and record that grade as its
    verdict, returning the candidates in proposal order."""
    proposals = [
        CardProposal(front=f"Q{index}", back=f"A{index}", quote=_CONTENT)
        for index in range(len(grades))
    ]
    run.add_round(round, proposals, _card_factory())
    candidates = run.of_round(round)
    run.record_verdicts(
        round,
        [
            CardVerdict(ref=candidate.ref, grade=grade, reasoning=f"reason-{index}")
            for index, (candidate, grade) in enumerate(
                zip(candidates, grades, strict=True)
            )
        ],
    )
    return candidates


def test_generating_instruction_leads_with_flow_language_task_then_note_verbatim() -> (
    None
):
    run = _run()
    builder = GeneratingInstructionBuilder()

    instruction = builder.build(run)

    assert _block_names(instruction) == (FLOW, LANGUAGE, TASK, NOTE)
    assert (
        builder.required
        == instruction.required
        == frozenset({FLOW, LANGUAGE, TASK, NOTE})
    )
    assert _block_text(instruction, NOTE) == run.note.content.value


def test_reviewing_instruction_renders_only_the_judged_rounds_candidates() -> None:
    run = _run()
    run.add_round(
        CandidateRound.FIRST,
        [
            CardProposal(front="Q1", back="A1", quote=_CONTENT),
            CardProposal(front="Q2", back="A2", quote=_CONTENT),
        ],
        _card_factory(),
    )
    run.add_round(
        CandidateRound.REPLACEMENT,
        [CardProposal(front="Q3", back="A3", quote=_CONTENT)],
        _card_factory(),
    )
    [replacement] = run.of_round(CandidateRound.REPLACEMENT)
    builder = ReviewingInstructionBuilder(CandidateRound.REPLACEMENT)

    instruction = builder.build(run)

    assert _block_names(instruction) == (FLOW, LANGUAGE, TASK, NOTE, CANDIDATES)
    assert builder.required == frozenset({FLOW, LANGUAGE, TASK, NOTE, CANDIDATES})
    candidates_text = _block_text(instruction, CANDIDATES)
    assert replacement.ref.value in candidates_text
    assert "Q3" in candidates_text
    for first_round_candidate in run.of_round(CandidateRound.FIRST):
        assert first_round_candidate.ref.value not in candidates_text


def test_regenerating_instruction_lists_first_round_gaps_with_their_failure() -> None:
    run = _run()
    [gap] = _reviewed(run, CandidateRound.FIRST, [ReviewGrade.WEAK])
    builder = RegeneratingInstructionBuilder()

    instruction = builder.build(run)

    assert _block_names(instruction) == (FLOW, LANGUAGE, TASK, NOTE, GAPS)
    assert builder.required == frozenset({FLOW, LANGUAGE, TASK, NOTE, GAPS})
    gaps_text = _block_text(instruction, GAPS)
    assert gap.failure is not None
    assert gap.ref.value in gaps_text
    assert gap.failure in gaps_text


def test_regenerating_instruction_explains_no_usable_cards_when_first_round_empty() -> (
    None
):
    run = _run()

    instruction = RegeneratingInstructionBuilder().build(run)

    gaps_text = _block_text(instruction, GAPS).lower()
    assert "no usable cards" in gaps_text
    assert "outright" in gaps_text


@pytest.mark.parametrize(
    ("grade", "expect_example"),
    [(ReviewGrade.SOUND, True), (ReviewGrade.WEAK, False)],
)
def test_regenerating_instruction_includes_accepted_example_only_when_accepted(
    grade: ReviewGrade, expect_example: bool
) -> None:
    run = _run()
    [candidate] = _reviewed(run, CandidateRound.FIRST, [grade])

    instruction = RegeneratingInstructionBuilder().build(run)

    assert (ACCEPTED_EXAMPLE in _block_names(instruction)) is expect_example
    assert (run.accepted_example() is candidate) is expect_example
    if expect_example:
        assert "Q0" in _block_text(instruction, ACCEPTED_EXAMPLE)


def test_merging_instruction_renders_merge_pool_candidates_by_ref() -> None:
    run = _run()
    [first_sound, first_weak] = _reviewed(
        run, CandidateRound.FIRST, [ReviewGrade.SOUND, ReviewGrade.WEAK]
    )
    [replacement_strong] = _reviewed(
        run, CandidateRound.REPLACEMENT, [ReviewGrade.STRONG]
    )
    builder = MergingInstructionBuilder()

    instruction = builder.build(run)

    assert _block_names(instruction) == (FLOW, LANGUAGE, TASK, CANDIDATES)
    assert builder.required == frozenset({FLOW, LANGUAGE, TASK, CANDIDATES})
    candidates_text = _block_text(instruction, CANDIDATES)
    assert first_sound.ref.value in candidates_text
    assert replacement_strong.ref.value in candidates_text
    assert first_weak.ref.value not in candidates_text
