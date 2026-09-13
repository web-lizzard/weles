from abc import ABC, abstractmethod
from typing import final, override

from domain.distill.run import CandidateRound, DistillRun
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
        raise NotImplementedError

    @final
    @override
    def build(self, context: DistillRun) -> Instruction:
        """The general blocks, then `phase_blocks`, as one `Instruction`."""
        raise NotImplementedError


class GeneratingInstructionBuilder(DistillInstructionBuilder):
    """First generation. Required: `TASK`, `NOTE`."""

    @property
    @override
    def phase_required(self) -> frozenset[str]:
        return frozenset({TASK, NOTE})

    @override
    def phase_blocks(self, context: DistillRun) -> tuple[InstructionBlock, ...]:
        raise NotImplementedError


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
        raise NotImplementedError


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
        raise NotImplementedError


class MergingInstructionBuilder(DistillInstructionBuilder):
    """Merge. Required: `TASK`, `CANDIDATES` — the merge pool under refs."""

    @property
    @override
    def phase_required(self) -> frozenset[str]:
        return frozenset({TASK, CANDIDATES})

    @override
    def phase_blocks(self, context: DistillRun) -> tuple[InstructionBlock, ...]:
        raise NotImplementedError
