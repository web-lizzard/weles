from datetime import UTC, datetime
from uuid import uuid4

from domain.distill.card_factory import CardFactory
from domain.distill.flow import (
    DistillMachine,
    Generating,
    Merging,
    Regenerating,
    Reviewing,
    ReviewingReplacements,
    regeneration_needed,
    regeneration_not_needed,
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
    CardVerdict,
    DistillPhase,
    NoteContent,
    NoteId,
    ReviewGrade,
    SessionId,
    TopicSnapshot,
)
from domain.shared.graph.model import StructuredState

_CONTENT = "Connections are established via a three-way handshake."


class _Deps:
    def __init__(self) -> None:
        self.card_factory: CardFactory = CardFactory(
            CardLengthPolicy(front_max=200, back_max=200)
        )


def _policy(threshold: float) -> RegenerationPolicy:
    return RegenerationPolicy(
        tiers=(ThresholdTier(max_length=None, min_accepted_share=threshold),)
    )


def _run(*, threshold: float = 0.5) -> DistillRun:
    note = mint_note(
        NoteId(value=uuid4()),
        SessionId(value=uuid4()),
        TopicSnapshot(id=uuid4(), label="TCP handshakes"),
        NoteContent(value=_CONTENT),
        [],
        datetime.now(UTC),
    )
    return DistillRun(
        note=note,
        document=NoteDocument.of(note.content),
        policy=_policy(threshold),
    )


def _reviewed_run(*, threshold: float, grades: list[ReviewGrade]) -> DistillRun:
    """A run whose first round already carries one candidate per grade,
    reviewed accordingly."""
    run = _run(threshold=threshold)
    proposals = [
        CardProposal(front=f"Q{index}", back=f"A{index}", quote=_CONTENT)
        for index in range(len(grades))
    ]
    run.add_round(CandidateRound.FIRST, proposals, _Deps().card_factory)
    candidates = run.of_round(CandidateRound.FIRST)
    run.record_verdicts(
        CandidateRound.FIRST,
        [
            CardVerdict(ref=candidate.ref, grade=grade, reasoning=f"reason-{index}")
            for index, (candidate, grade) in enumerate(
                zip(candidates, grades, strict=True)
            )
        ],
    )
    return run


def _machine(run: DistillRun) -> DistillMachine:
    return DistillMachine(run, _Deps())


def test_distill_graph_is_acyclic_with_merging_the_only_terminal_structured_state() -> (
    None
):
    graph = _machine(_run()).graph

    assert graph.terminal_states == frozenset({DistillPhase.MERGING})
    for source, targets in graph.transitions.items():
        assert source not in targets
    assert all(isinstance(state, StructuredState) for state in graph.states.values())


def test_regeneration_guards_are_mutually_exclusive_above_and_below_threshold() -> None:
    clears_threshold = _reviewed_run(
        threshold=0.5, grades=[ReviewGrade.SOUND, ReviewGrade.WEAK]
    )
    misses_threshold = _reviewed_run(
        threshold=0.9, grades=[ReviewGrade.SOUND, ReviewGrade.WEAK]
    )

    assert regeneration_needed(clears_threshold) is False
    assert regeneration_not_needed(clears_threshold) is True
    assert regeneration_needed(misses_threshold) is True
    assert regeneration_not_needed(misses_threshold) is False


def test_current_state_build_instruction_and_enter_state_resolve_from_run_phase() -> (
    None
):
    run = _run()
    run.phase = DistillPhase.REVIEWING
    machine = _machine(run)

    assert machine.current_state_name is DistillPhase.REVIEWING
    assert isinstance(machine.current_state, Reviewing)
    assert machine.build_instruction() == Reviewing().instruction_builder.build(run)

    machine.enter_state(run, DistillPhase.MERGING)

    assert run.phase is DistillPhase.MERGING
    assert machine.current_state_name is DistillPhase.MERGING
    assert isinstance(machine.current_state, Merging)


def test_output_without_model_answers_directly_only_when_nothing_needs_judgment() -> (
    None
):
    deps = _Deps()
    idle_run = _run()
    awaiting_first_review = _run()
    awaiting_first_review.add_round(
        CandidateRound.FIRST,
        [CardProposal(front="Q1", back="A1", quote=_CONTENT)],
        deps.card_factory,
    )
    awaiting_replacement_review = _run()
    awaiting_replacement_review.add_round(
        CandidateRound.REPLACEMENT,
        [CardProposal(front="Q1", back="A1", quote=_CONTENT)],
        deps.card_factory,
    )
    single_card_pool = _reviewed_run(threshold=0.0, grades=[ReviewGrade.SOUND])
    two_card_pool = _reviewed_run(
        threshold=0.0, grades=[ReviewGrade.SOUND, ReviewGrade.STRONG]
    )

    assert Generating().output_without_model(idle_run) is None
    assert Generating().output_without_model(awaiting_first_review) is None
    assert Regenerating().output_without_model(idle_run) is None
    assert Regenerating().output_without_model(awaiting_first_review) is None

    assert Reviewing().output_without_model(idle_run) == CardsReviewed(verdicts=[])
    assert Reviewing().output_without_model(awaiting_first_review) is None
    assert ReviewingReplacements().output_without_model(idle_run) == CardsReviewed(
        verdicts=[]
    )
    assert (
        ReviewingReplacements().output_without_model(awaiting_replacement_review)
        is None
    )

    assert Merging().output_without_model(idle_run) == DuplicatesFound(groups=[])
    assert Merging().output_without_model(single_card_pool) == DuplicatesFound(
        groups=[]
    )
    assert Merging().output_without_model(two_card_pool) is None


async def test_direct_route_ends_in_merging_when_first_round_clears_threshold() -> None:
    run = _run(threshold=0.5)
    machine = _machine(run)

    await machine.apply(
        CardsProposed(proposals=[CardProposal(front="Q1", back="A1", quote=_CONTENT)])
    )
    assert await machine.advance() is True
    assert machine.current_state_name is DistillPhase.REVIEWING

    [candidate] = run.of_round(CandidateRound.FIRST)
    await machine.apply(
        CardsReviewed(
            verdicts=[
                CardVerdict(ref=candidate.ref, grade=ReviewGrade.SOUND, reasoning="ok")
            ]
        )
    )
    assert await machine.advance() is True
    assert machine.current_state_name is DistillPhase.MERGING

    assert await machine.advance() is False
    assert machine.current_state_name is DistillPhase.MERGING


async def test_regenerating_route_walk_ends_in_merging_via_replacement_review() -> None:
    run = _run(threshold=0.9)
    machine = _machine(run)

    await machine.apply(
        CardsProposed(proposals=[CardProposal(front="Q1", back="A1", quote=_CONTENT)])
    )
    assert await machine.advance() is True
    assert machine.current_state_name is DistillPhase.REVIEWING

    [first] = run.of_round(CandidateRound.FIRST)
    await machine.apply(
        CardsReviewed(
            verdicts=[
                CardVerdict(
                    ref=first.ref, grade=ReviewGrade.WEAK, reasoning="not solid"
                )
            ]
        )
    )
    assert await machine.advance() is True
    assert machine.current_state_name is DistillPhase.REGENERATING

    await machine.apply(
        CardsProposed(proposals=[CardProposal(front="Q2", back="A2", quote=_CONTENT)])
    )
    assert await machine.advance() is True
    assert machine.current_state_name is DistillPhase.REVIEWING_REPLACEMENTS

    [replacement] = run.of_round(CandidateRound.REPLACEMENT)
    await machine.apply(
        CardsReviewed(
            verdicts=[
                CardVerdict(
                    ref=replacement.ref, grade=ReviewGrade.SOUND, reasoning="fixed"
                )
            ]
        )
    )
    assert await machine.advance() is True
    assert machine.current_state_name is DistillPhase.MERGING

    assert await machine.advance() is False
    assert machine.current_state_name is DistillPhase.MERGING
