from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import pytest

from adapters.out.in_memory.distill.structured_task import (
    DeterministicStructuredTaskAdapter,
)
from domain.distill.card_factory import CardFactory
from domain.distill.instructions import (
    GeneratingInstructionBuilder,
    MergingInstructionBuilder,
    ReviewingInstructionBuilder,
)
from domain.distill.note import mint_note
from domain.distill.note_document import NoteDocument
from domain.distill.ports import StructuredTaskPort
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
from domain.shared.identity.model import UserId

_IMPLEMENTATIONS: list[Callable[[], StructuredTaskPort]] = [
    cast(Callable[[], StructuredTaskPort], DeterministicStructuredTaskAdapter),
]

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
        UserId.new(),
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


@pytest.mark.parametrize("make_port", _IMPLEMENTATIONS, ids=["deterministic"])
async def test_each_answer_validates_as_the_requested_output_type(
    make_port: Callable[[], StructuredTaskPort],
) -> None:
    port = make_port()
    review_run = _run()
    review_run.add_round(
        CandidateRound.FIRST,
        [CardProposal(front="Q1", back="A1", quote=_CONTENT)],
        _card_factory(),
    )

    proposed = await port.complete(
        GeneratingInstructionBuilder().build(_run()), CardsProposed
    )
    reviewed = await port.complete(
        ReviewingInstructionBuilder(CandidateRound.FIRST).build(review_run),
        CardsReviewed,
    )
    duplicates = await port.complete(
        MergingInstructionBuilder().build(_run()), DuplicatesFound
    )

    assert isinstance(proposed, CardsProposed)
    assert isinstance(reviewed, CardsReviewed)
    assert isinstance(duplicates, DuplicatesFound)


@pytest.mark.parametrize("make_port", _IMPLEMENTATIONS, ids=["deterministic"])
async def test_generation_is_deterministic_for_the_same_instruction(
    make_port: Callable[[], StructuredTaskPort],
) -> None:
    port = make_port()
    instruction = GeneratingInstructionBuilder().build(_run())

    first = await port.complete(instruction, CardsProposed)
    second = await port.complete(instruction, CardsProposed)

    assert first == second


@pytest.mark.parametrize("make_port", _IMPLEMENTATIONS, ids=["deterministic"])
async def test_a_review_names_only_refs_from_the_instruction(
    make_port: Callable[[], StructuredTaskPort],
) -> None:
    port = make_port()
    run = _run()
    run.add_round(
        CandidateRound.FIRST,
        [
            CardProposal(front="Q1", back="A1", quote=_CONTENT),
            CardProposal(front="Q2", back="A2", quote=_CONTENT),
        ],
        _card_factory(),
    )
    known_refs = {
        candidate.ref for candidate in run.awaiting_review(CandidateRound.FIRST)
    }
    instruction = ReviewingInstructionBuilder(CandidateRound.FIRST).build(run)

    reviewed = await port.complete(instruction, CardsReviewed)

    assert {verdict.ref for verdict in reviewed.verdicts} <= known_refs
