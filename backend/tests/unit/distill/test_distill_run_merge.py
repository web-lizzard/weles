from datetime import UTC, datetime
from uuid import uuid4

from domain.distill.card_factory import CardFactory
from domain.distill.note import mint_note
from domain.distill.note_document import NoteDocument
from domain.distill.regeneration import RegenerationPolicy, ThresholdTier
from domain.distill.run import Candidate, CandidateRound, DistillRun
from domain.distill.value_objects import (
    CandidateRef,
    CardLengthPolicy,
    CardProposal,
    CardVerdict,
    DiscardReason,
    DuplicateGroup,
    NoteContent,
    NoteId,
    ReviewGrade,
    SessionId,
    TopicSnapshot,
)

_CONTENT = "Connections are established via a three-way handshake."
_QUOTE = _CONTENT


def _policy() -> RegenerationPolicy:
    return RegenerationPolicy(
        tiers=(
            ThresholdTier(max_length=1500, min_accepted_share=0.5),
            ThresholdTier(max_length=6000, min_accepted_share=0.6),
            ThresholdTier(max_length=None, min_accepted_share=0.7),
        )
    )


def _run() -> DistillRun:
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
        policy=_policy(),
    )


def _factory() -> CardFactory:
    return CardFactory(CardLengthPolicy(front_max=200, back_max=200))


def _reviewed(
    run: DistillRun, round: CandidateRound, grades: list[ReviewGrade]
) -> list[Candidate]:
    """Add one proposal per grade to `round` and record that grade as its
    verdict, returning the candidates in proposal order."""
    proposals = [
        CardProposal(front=f"Q{index}", back=f"A{index}", quote=_QUOTE)
        for index in range(len(grades))
    ]
    run.add_round(round, proposals, _factory())
    candidates = run.of_round(round)
    run.record_verdicts(
        round,
        [
            CardVerdict(ref=candidate.ref, grade=grade, reasoning="n/a")
            for candidate, grade in zip(candidates, grades, strict=True)
        ],
    )
    return candidates


def test_merge_pool_orders_accepted_candidates_across_both_rounds() -> None:
    run = _run()
    first_sound, first_weak = _reviewed(
        run, CandidateRound.FIRST, [ReviewGrade.SOUND, ReviewGrade.WEAK]
    )
    [replacement_strong] = _reviewed(
        run, CandidateRound.REPLACEMENT, [ReviewGrade.STRONG]
    )

    assert first_weak.accepted is False
    assert run.merge_pool() == [first_sound, replacement_strong]


def test_discard_duplicates_keeps_the_higher_grade_candidate_in_a_duplicate_group() -> (
    None
):
    run = _run()
    weaker, stronger = _reviewed(
        run, CandidateRound.FIRST, [ReviewGrade.SOUND, ReviewGrade.STRONG]
    )

    run.discard_duplicates(
        [DuplicateGroup(refs=(weaker.ref, stronger.ref), reasoning="same fact")]
    )

    assert stronger.card is not None
    assert stronger.card.discard is None
    assert weaker.card is not None
    assert weaker.card.discard is not None
    assert weaker.card.discard.reason == DiscardReason.DUPLICATE
    assert weaker.card.discard.detail == "same fact"


def test_discard_duplicates_prefers_replacement_over_first_round_on_equal_grade() -> (
    None
):
    run = _run()
    [first] = _reviewed(run, CandidateRound.FIRST, [ReviewGrade.SOUND])
    [replacement] = _reviewed(run, CandidateRound.REPLACEMENT, [ReviewGrade.SOUND])

    run.discard_duplicates(
        [DuplicateGroup(refs=(first.ref, replacement.ref), reasoning="same fact")]
    )

    assert replacement.card is not None
    assert replacement.card.discard is None
    assert first.card is not None
    assert first.card.discard is not None
    assert first.card.discard.reason == DiscardReason.DUPLICATE


def test_discard_duplicates_prefers_the_earlier_ref_on_equal_grade_same_round() -> None:
    run = _run()
    earlier, later = _reviewed(
        run, CandidateRound.FIRST, [ReviewGrade.SOUND, ReviewGrade.SOUND]
    )

    run.discard_duplicates(
        [DuplicateGroup(refs=(later.ref, earlier.ref), reasoning="same fact")]
    )

    assert earlier.card is not None
    assert earlier.card.discard is None
    assert later.card is not None
    assert later.card.discard is not None
    assert later.card.discard.reason == DiscardReason.DUPLICATE


def test_discard_duplicates_ignores_non_pool_refs_and_is_a_noop_below_two_members() -> (
    None
):
    run = _run()
    [accepted] = _reviewed(run, CandidateRound.FIRST, [ReviewGrade.SOUND])
    [rejected] = _reviewed(run, CandidateRound.REPLACEMENT, [ReviewGrade.WEAK])

    run.discard_duplicates(
        [
            DuplicateGroup(
                refs=(accepted.ref, rejected.ref, CandidateRef(value="c99")),
                reasoning="same fact",
            )
        ]
    )

    assert accepted.card is not None
    assert accepted.card.discard is None
