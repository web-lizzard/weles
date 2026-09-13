from abc import ABC
from collections.abc import Sequence
from typing import override

from domain.distill.deps import DistillDeps
from domain.distill.instructions import (
    DistillInstructionBuilder,
    GeneratingInstructionBuilder,
    MergingInstructionBuilder,
    RegeneratingInstructionBuilder,
    ReviewingInstructionBuilder,
)
from domain.distill.run import (
    CandidateRound,
    CardsProposed,
    CardsReviewed,
    DistillEvent,
    DistillRun,
    DuplicatesFound,
)
from domain.distill.value_objects import DistillPhase
from domain.shared.graph.machine import StructuredStateMachine
from domain.shared.graph.model import (
    Action,
    Graph,
    StructuredState,
    Tool,
    ToolResult,
    Transition,
)
from domain.shared.instruction.model import Instruction


class DistillMachine(
    StructuredStateMachine[DistillRun, DistillDeps, DistillEvent, DistillPhase]
):
    """Distill's phase graph, bound to one run.

    Supplies the graph and the run hooks. The command walks it: apply each
    phase's result (from `output_without_model` or the model), then `advance`,
    until `advance` refuses; the run has finished when the phase it stopped in
    is terminal.
    """

    @property
    @override
    def graph(
        self,
    ) -> Graph[DistillRun, DistillDeps, DistillEvent, DistillPhase]:
        return _DISTILL_GRAPH

    @property
    @override
    def current_state(
        self,
    ) -> StructuredState[DistillRun, DistillDeps, DistillEvent]: ...

    @override
    def state_name_of(self, context: DistillRun) -> DistillPhase: ...

    @override
    def enter_state(self, context: DistillRun, name: DistillPhase) -> None: ...

    @override
    def build_instruction(self) -> Instruction: ...


class _DistillState(StructuredState[DistillRun, DistillDeps, DistillEvent], ABC):
    """What every distill phase shares: no tools — each answers once, in its
    output — and no model-read description, since guards alone route."""

    @property
    @override
    def tools(self) -> Sequence[Tool[DistillRun, ToolResult]]:
        return ()

    @property
    @override
    def description(self) -> str:
        return ""


class Generating(_DistillState):
    """First generation. Its result mints the first round: every proposal
    becomes a candidate, gated by anchor and length on the way in. Always asks
    the model."""

    @property
    @override
    def output(self) -> type[CardsProposed]:
        return CardsProposed

    @property
    @override
    def instruction_builder(self) -> DistillInstructionBuilder:
        return _GENERATING_INSTRUCTION_BUILDER

    @property
    @override
    def actions(self) -> Sequence[Action[DistillRun, DistillDeps, DistillEvent]]:
        return (_mint_first_round,)

    @override
    def output_without_model(self, context: DistillRun) -> DistillEvent | None: ...


class Reviewing(_DistillState):
    """First review: judges the first round's candidates awaiting review.
    Answers an empty verdict list without the model when there are none."""

    @property
    @override
    def output(self) -> type[CardsReviewed]:
        return CardsReviewed

    @property
    @override
    def instruction_builder(self) -> DistillInstructionBuilder:
        return _FIRST_REVIEW_INSTRUCTION_BUILDER

    @property
    @override
    def actions(self) -> Sequence[Action[DistillRun, DistillDeps, DistillEvent]]:
        return (_record_first_review,)

    @override
    def output_without_model(self, context: DistillRun) -> DistillEvent | None: ...


class Regenerating(_DistillState):
    """Replacement generation, for the first round's gaps. Its result mints the
    replacement round through the same gates. Always asks the model — a run
    reaches it only below threshold, which includes a first round with no
    proposals at all."""

    @property
    @override
    def output(self) -> type[CardsProposed]:
        return CardsProposed

    @property
    @override
    def instruction_builder(self) -> DistillInstructionBuilder:
        return _REGENERATING_INSTRUCTION_BUILDER

    @property
    @override
    def actions(self) -> Sequence[Action[DistillRun, DistillDeps, DistillEvent]]:
        return (_mint_replacements,)

    @override
    def output_without_model(self, context: DistillRun) -> DistillEvent | None: ...


class ReviewingReplacements(_DistillState):
    """Second review: judges replacements only; first-round verdicts stand.
    Answers an empty verdict list without the model when there are none."""

    @property
    @override
    def output(self) -> type[CardsReviewed]:
        return CardsReviewed

    @property
    @override
    def instruction_builder(self) -> DistillInstructionBuilder:
        return _REPLACEMENT_REVIEW_INSTRUCTION_BUILDER

    @property
    @override
    def actions(self) -> Sequence[Action[DistillRun, DistillDeps, DistillEvent]]:
        return (_record_replacement_review,)

    @override
    def output_without_model(self, context: DistillRun) -> DistillEvent | None: ...


class Merging(_DistillState):
    """The terminal phase: discards all but one card of each duplicate group.
    Answers no groups without the model when the pool holds fewer than two
    cards."""

    @property
    @override
    def output(self) -> type[DuplicatesFound]:
        return DuplicatesFound

    @property
    @override
    def instruction_builder(self) -> DistillInstructionBuilder:
        return _MERGING_INSTRUCTION_BUILDER

    @property
    @override
    def actions(self) -> Sequence[Action[DistillRun, DistillDeps, DistillEvent]]:
        return (_discard_duplicates,)

    @override
    def output_without_model(self, context: DistillRun) -> DistillEvent | None: ...


def regeneration_needed(context: DistillRun) -> bool:
    """Guard into regeneration. Exactly one of this and
    `regeneration_not_needed` passes for any run — the exclusivity `advance`
    relies on, held by construction."""
    return context.regeneration_needed()


def regeneration_not_needed(context: DistillRun) -> bool:
    """Guard from the first review straight to merge: the negation of
    `regeneration_needed`."""
    return not context.regeneration_needed()


async def _mint_first_round(
    context: DistillRun, deps: DistillDeps, event: DistillEvent
) -> None:
    """On `CardsProposed`: the first round, through the gates."""
    if isinstance(event, CardsProposed):
        context.add_round(CandidateRound.FIRST, event.proposals, deps.card_factory)


async def _mint_replacements(
    context: DistillRun, deps: DistillDeps, event: DistillEvent
) -> None:
    """On `CardsProposed`: the replacement round, through the same gates."""
    if isinstance(event, CardsProposed):
        context.add_round(
            CandidateRound.REPLACEMENT, event.proposals, deps.card_factory
        )


async def _record_first_review(
    context: DistillRun, deps: DistillDeps, event: DistillEvent
) -> None:
    """On `CardsReviewed`: verdicts on the first round."""
    _ = deps
    if isinstance(event, CardsReviewed):
        context.record_verdicts(CandidateRound.FIRST, event.verdicts)


async def _record_replacement_review(
    context: DistillRun, deps: DistillDeps, event: DistillEvent
) -> None:
    """On `CardsReviewed`: verdicts on replacements only; first-round verdicts
    stand."""
    _ = deps
    if isinstance(event, CardsReviewed):
        context.record_verdicts(CandidateRound.REPLACEMENT, event.verdicts)


async def _discard_duplicates(
    context: DistillRun, deps: DistillDeps, event: DistillEvent
) -> None:
    """On `DuplicatesFound`: all but one member of each group discarded."""
    _ = deps
    if isinstance(event, DuplicatesFound):
        context.discard_duplicates(event.groups)


_GENERATING_INSTRUCTION_BUILDER = GeneratingInstructionBuilder()
_FIRST_REVIEW_INSTRUCTION_BUILDER = ReviewingInstructionBuilder(CandidateRound.FIRST)
_REGENERATING_INSTRUCTION_BUILDER = RegeneratingInstructionBuilder()
_REPLACEMENT_REVIEW_INSTRUCTION_BUILDER = ReviewingInstructionBuilder(
    CandidateRound.REPLACEMENT
)
_MERGING_INSTRUCTION_BUILDER = MergingInstructionBuilder()

_DISTILL_GRAPH = Graph[DistillRun, DistillDeps, DistillEvent, DistillPhase](
    states={
        DistillPhase.GENERATING: Generating(),
        DistillPhase.REVIEWING: Reviewing(),
        DistillPhase.REGENERATING: Regenerating(),
        DistillPhase.REVIEWING_REPLACEMENTS: ReviewingReplacements(),
        DistillPhase.MERGING: Merging(),
    },
    # Acyclic, and MERGING is the only terminal state: regeneration happens at
    # most once because no edge leads back, not because anything counts.
    transitions={
        DistillPhase.GENERATING: {
            DistillPhase.REVIEWING: Transition[DistillRun, DistillDeps, DistillEvent](),
        },
        DistillPhase.REVIEWING: {
            DistillPhase.REGENERATING: Transition[
                DistillRun, DistillDeps, DistillEvent
            ](guard=regeneration_needed),
            DistillPhase.MERGING: Transition[DistillRun, DistillDeps, DistillEvent](
                guard=regeneration_not_needed
            ),
        },
        DistillPhase.REGENERATING: {
            DistillPhase.REVIEWING_REPLACEMENTS: Transition[
                DistillRun, DistillDeps, DistillEvent
            ](),
        },
        DistillPhase.REVIEWING_REPLACEMENTS: {
            DistillPhase.MERGING: Transition[DistillRun, DistillDeps, DistillEvent](),
        },
    },
)
