from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import final, override

from domain.distill.run import Candidate, CandidateRound, DistillRun
from domain.shared.instruction.model import (
    Instruction,
    InstructionBlock,
    InstructionBuilder,
)

FLOW = "flow"
LANGUAGE = "language"
TASK = "task"
NOTE = "note"
CANDIDATES = "candidates"
GAPS = "gaps"
ACCEPTED_EXAMPLE = "accepted_example"
"""The names of distill's blocks — constants for the reason capture's are
(`domain/capture/instructions.py`): a builder's required set and its tests
refer to blocks by name."""


class DistillInstructionBuilder(InstructionBuilder[DistillRun], ABC):
    """The shape every distill phase's builder takes, mirroring capture's: a
    general floor (`FLOW`, `LANGUAGE`) every phase carries, then the phase's
    own blocks. `build` composes them, so the required set a phase advertises
    and the one its instruction carries cannot disagree.

    No block restates the output schema — that reaches the model through the
    provider's structured-output channel, the way tools do in capture.
    """

    @property
    @abstractmethod
    def phase_required(self) -> frozenset[str]:
        """The blocks this phase can never omit, beyond the general floor."""
        ...

    @abstractmethod
    def phase_blocks(self, context: DistillRun) -> tuple[InstructionBlock, ...]:
        """This phase's blocks for the run as it stands, in reading order."""
        ...

    @property
    @final
    @override
    def required(self) -> frozenset[str]:
        return _GENERAL_REQUIRED | self.phase_required

    @final
    @override
    def build(self, context: DistillRun) -> Instruction:
        """The general blocks, then `phase_blocks`, as one `Instruction`."""
        blocks = (_FLOW, _LANGUAGE, *self.phase_blocks(context))
        return Instruction(blocks=blocks, required=self.required)


class GeneratingInstructionBuilder(DistillInstructionBuilder):
    """First generation. Required: `TASK`, `NOTE`."""

    @property
    @override
    def phase_required(self) -> frozenset[str]:
        return frozenset({TASK, NOTE})

    @override
    def phase_blocks(self, context: DistillRun) -> tuple[InstructionBlock, ...]:
        return (_GENERATING_TASK, _note_block(context))


class ReviewingInstructionBuilder(DistillInstructionBuilder):
    """Both reviews. Required: `TASK`, `NOTE`, `CANDIDATES` — the candidates
    awaiting review in the round the phase judges, each under its ref.

    One builder, two phases: phase identity is not instruction identity. The
    round is the builder's only parameter.
    """

    def __init__(self, round_: CandidateRound) -> None:
        self._round: CandidateRound = round_

    @property
    @override
    def phase_required(self) -> frozenset[str]:
        return frozenset({TASK, NOTE, CANDIDATES})

    @override
    def phase_blocks(self, context: DistillRun) -> tuple[InstructionBlock, ...]:
        candidates = context.awaiting_review(self._round)
        return (
            _REVIEWING_TASK,
            _note_block(context),
            InstructionBlock(name=CANDIDATES, text=_render_candidates(candidates)),
        )


class RegeneratingInstructionBuilder(DistillInstructionBuilder):
    """Replacement generation. Required: `TASK`, `NOTE`, `GAPS` — each failed
    first-round card with why it failed; when the first round had none (no
    proposals at all), the block says so and asks for cards outright.

    Optional: `ACCEPTED_EXAMPLE`, present only when review accepted a
    first-round card.
    """

    @property
    @override
    def phase_required(self) -> frozenset[str]:
        return frozenset({TASK, NOTE, GAPS})

    @override
    def phase_blocks(self, context: DistillRun) -> tuple[InstructionBlock, ...]:
        gaps = context.gaps()
        if gaps:
            gaps_text = "\n".join(f"{gap.ref.value}: {gap.failure}" for gap in gaps)
        else:
            gaps_text = _NO_USABLE_CARDS_TEXT
        blocks: list[InstructionBlock] = [
            _REGENERATING_TASK,
            _note_block(context),
            InstructionBlock(name=GAPS, text=gaps_text),
        ]
        example = context.accepted_example()
        if example is not None:
            blocks.append(
                InstructionBlock(name=ACCEPTED_EXAMPLE, text=_render_candidate(example))
            )
        return tuple(blocks)


class MergingInstructionBuilder(DistillInstructionBuilder):
    """Merge. Required: `TASK`, `CANDIDATES` — the merge pool under refs."""

    @property
    @override
    def phase_required(self) -> frozenset[str]:
        return frozenset({TASK, CANDIDATES})

    @override
    def phase_blocks(self, context: DistillRun) -> tuple[InstructionBlock, ...]:
        return (
            _MERGING_TASK,
            InstructionBlock(
                name=CANDIDATES, text=_render_candidates(context.merge_pool())
            ),
        )


_GENERAL_REQUIRED = frozenset({FLOW, LANGUAGE})

_FLOW = InstructionBlock(
    name=FLOW,
    text=(
        "You are generating flashcards from one approved note. Every surviving "
        "card must be grounded in the note's own words — never invented, never "
        "drawn from outside knowledge. The run walks several phases in "
        "sequence: you see only the phase you are on now, not the ones before "
        "or after it."
    ),
)

_LANGUAGE = InstructionBlock(
    name=LANGUAGE,
    text="Write every card and every piece of reasoning in the note's own language.",
)

_GENERATING_TASK = InstructionBlock(
    name=TASK,
    text=(
        "Propose question/answer flashcards grounded in the note below. Each "
        "card's quote must be copied verbatim from the note — the exact words "
        "the card is anchored to. How many cards to propose is your call: "
        "propose one per distinct fact worth remembering, and none for "
        "material that does not stand on its own."
    ),
)

_REVIEWING_TASK = InstructionBlock(
    name=TASK,
    text=(
        "Grade each candidate card below on the scale poor, weak, sound, "
        "strong, and give your reasoning for the grade. Judge each by ref: "
        "does it hold up on its own, grounded in the note, worth keeping."
    ),
)

_REGENERATING_TASK = InstructionBlock(
    name=TASK,
    text=(
        "Propose replacement cards for the gaps below, grounded in the note "
        "the same way as before. Do not repeat a card already accepted."
    ),
)

_MERGING_TASK = InstructionBlock(
    name=TASK,
    text=(
        "Group the candidate cards below that say the same thing, and give "
        "your reasoning for each grouping. A card with nothing to group with "
        "needs no group."
    ),
)

_NO_USABLE_CARDS_TEXT = (
    "There are no usable cards from the first round; propose cards outright."
)


def _note_block(run: DistillRun) -> InstructionBlock:
    """The note's content, verbatim, as its own block — the way Phase 8's
    deterministic adapter recovers it back out."""
    return InstructionBlock(name=NOTE, text=run.note.content.value)


def _render_candidates(candidates: Sequence[Candidate]) -> str:
    """One line per candidate, under its ref, so a model or a test can find
    a candidate's proposal by name."""
    return "\n".join(_render_candidate_line(candidate) for candidate in candidates)


def _render_candidate_line(candidate: Candidate) -> str:
    proposal = candidate.proposal
    return (
        f"{candidate.ref.value}: Q: {proposal.front} / A: {proposal.back} "
        f'(quote: "{proposal.quote}")'
    )


def _render_candidate(candidate: Candidate) -> str:
    """One candidate's proposal on its own, for `ACCEPTED_EXAMPLE`."""
    proposal = candidate.proposal
    return f"Q: {proposal.front} / A: {proposal.back}"
