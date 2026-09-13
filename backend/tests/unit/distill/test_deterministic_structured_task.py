from datetime import UTC, datetime
from uuid import uuid4

from adapters.out.in_memory.distill.structured_task import (
    DeterministicStructuredTaskAdapter,
)
from domain.distill.card_factory import CardFactory
from domain.distill.instructions import (
    GeneratingInstructionBuilder,
    MergingInstructionBuilder,
    RegeneratingInstructionBuilder,
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
    ReviewGrade,
    SessionId,
    TopicSnapshot,
)

_TWO_BLOCK_NOTE = (
    "TCP begins the handshake. The client sends a SYN packet first.\n"
    "\n"
    "The server responds with SYN-ACK. It waits for the final ACK.\n"
)
_FIRST_BLOCK_QUOTE = "TCP begins the handshake. The client sends a SYN packet first."

_FABRICATED_FRONT = "What is the capital of Wonderland?"
_FABRICATED_BACK = (
    "There is no such capital; this proposal is a deliberate control card"
    " used to exercise the ungrounded-discard path end to end."
)
_FABRICATED_QUOTE = "no note is ever expected to contain this exact sentinel phrase"


def _policy() -> RegenerationPolicy:
    return RegenerationPolicy(
        tiers=(
            ThresholdTier(max_length=1500, min_accepted_share=0.5),
            ThresholdTier(max_length=6000, min_accepted_share=0.6),
            ThresholdTier(max_length=None, min_accepted_share=0.7),
        )
    )


def _run(content: str = _TWO_BLOCK_NOTE) -> DistillRun:
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


async def test_a_generated_proposal_carries_the_fabricated_control_card() -> None:
    port = DeterministicStructuredTaskAdapter()
    instruction = GeneratingInstructionBuilder().build(_run())

    proposed = await port.complete(instruction, CardsProposed)

    control = [p for p in proposed.proposals if p.quote == _FABRICATED_QUOTE]
    assert len(control) == 1
    assert control[0].front == _FABRICATED_FRONT
    assert control[0].back == _FABRICATED_BACK


async def test_a_regenerating_instruction_yields_no_proposals() -> None:
    port = DeterministicStructuredTaskAdapter()
    instruction = RegeneratingInstructionBuilder().build(_run())

    proposed = await port.complete(instruction, CardsProposed)

    assert proposed.proposals == []


async def test_a_review_grades_every_awaiting_candidate_sound_with_one_reasoning() -> (
    None
):
    port = DeterministicStructuredTaskAdapter()
    run = _run()
    run.add_round(
        CandidateRound.FIRST,
        [
            CardProposal(front="Q1", back="A1", quote=_FIRST_BLOCK_QUOTE),
            CardProposal(front="Q2", back="A2", quote=_FIRST_BLOCK_QUOTE),
        ],
        _card_factory(),
    )
    known_refs = {c.ref for c in run.awaiting_review(CandidateRound.FIRST)}
    instruction = ReviewingInstructionBuilder(CandidateRound.FIRST).build(run)

    reviewed = await port.complete(instruction, CardsReviewed)

    assert {v.ref for v in reviewed.verdicts} == known_refs
    assert all(v.grade == ReviewGrade.SOUND for v in reviewed.verdicts)
    reasonings = {v.reasoning for v in reviewed.verdicts}
    assert len(reasonings) == 1
    assert next(iter(reasonings)) != ""


async def test_merging_finds_no_duplicate_groups() -> None:
    port = DeterministicStructuredTaskAdapter()
    instruction = MergingInstructionBuilder().build(_run())

    duplicates = await port.complete(instruction, DuplicatesFound)

    assert duplicates.groups == []
