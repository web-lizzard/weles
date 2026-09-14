from datetime import UTC, datetime
from uuid import uuid4

from domain.distill.card_factory import CardFactory
from domain.distill.note import mint_note
from domain.distill.note_document import NoteDocument
from domain.distill.regeneration import RegenerationPolicy, ThresholdTier
from domain.distill.run import CandidateRound, DistillRun
from domain.distill.value_objects import (
    CandidateRef,
    CardLengthPolicy,
    CardProposal,
    CardVerdict,
    DiscardReason,
    NoteContent,
    NoteId,
    ReviewGrade,
    SessionId,
    TopicSnapshot,
)
from domain.shared.identity.model import UserId

_CONTENT = "Connections are established via a three-way handshake."
_QUOTE = "Connections are established via a three-way handshake."


def _policy() -> RegenerationPolicy:
    return RegenerationPolicy(
        tiers=(
            ThresholdTier(max_length=1500, min_accepted_share=0.5),
            ThresholdTier(max_length=6000, min_accepted_share=0.6),
            ThresholdTier(max_length=None, min_accepted_share=0.7),
        )
    )


def _run(content: str) -> DistillRun:
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


def _factory() -> CardFactory:
    return CardFactory(CardLengthPolicy(front_max=30, back_max=40))


def test_record_verdicts_marks_a_passing_grade_as_accepted_with_no_discard() -> None:
    run = _run(_CONTENT)
    run.add_round(
        CandidateRound.FIRST,
        [
            CardProposal(
                front="What starts a connection?", back="A handshake.", quote=_QUOTE
            )
        ],
        _factory(),
    )
    [candidate] = run.of_round(CandidateRound.FIRST)

    run.record_verdicts(
        CandidateRound.FIRST,
        [
            CardVerdict(
                ref=candidate.ref,
                grade=ReviewGrade.SOUND,
                reasoning="clear and grounded",
            )
        ],
    )

    assert candidate.verdict is not None
    assert candidate.verdict.grade is ReviewGrade.SOUND
    assert candidate.accepted is True
    assert candidate.card is not None
    assert candidate.card.discard is None
    assert candidate.failure is None


def test_record_verdicts_discards_a_non_passing_grade_as_low_quality() -> None:
    run = _run(_CONTENT)
    run.add_round(
        CandidateRound.FIRST,
        [
            CardProposal(
                front="What starts a connection?", back="A handshake.", quote=_QUOTE
            )
        ],
        _factory(),
    )
    [candidate] = run.of_round(CandidateRound.FIRST)

    run.record_verdicts(
        CandidateRound.FIRST,
        [CardVerdict(ref=candidate.ref, grade=ReviewGrade.WEAK, reasoning="too vague")],
    )

    assert candidate.accepted is False
    assert candidate.card is not None
    assert candidate.card.discard is not None
    assert candidate.card.discard.reason == DiscardReason.LOW_QUALITY
    assert candidate.card.discard.detail == "too vague"
    assert candidate.failure == f"{DiscardReason.LOW_QUALITY}: too vague"


def test_record_verdicts_ignores_unrelated_refs_and_marks_unnamed_no_verdict() -> None:
    run = _run(_CONTENT)
    run.add_round(
        CandidateRound.FIRST,
        [
            CardProposal(
                front="What starts a connection?", back="A handshake.", quote=_QUOTE
            )
        ],
        _factory(),
    )
    run.add_round(
        CandidateRound.REPLACEMENT,
        [CardProposal(front="Who initiates?", back="The client.", quote=_QUOTE)],
        _factory(),
    )
    [first_candidate] = run.of_round(CandidateRound.FIRST)
    [replacement_candidate] = run.of_round(CandidateRound.REPLACEMENT)

    run.record_verdicts(
        CandidateRound.FIRST,
        [
            CardVerdict(
                ref=replacement_candidate.ref, grade=ReviewGrade.SOUND, reasoning="n/a"
            ),
            CardVerdict(
                ref=CandidateRef(value="c99"), grade=ReviewGrade.SOUND, reasoning="n/a"
            ),
        ],
    )

    assert first_candidate.verdict is not None
    assert first_candidate.card is not None
    assert first_candidate.card.discard is not None
    assert first_candidate.card.discard.reason == DiscardReason.LOW_QUALITY
    assert first_candidate.card.discard.detail == "no verdict"
    assert first_candidate.failure == f"{DiscardReason.LOW_QUALITY}: no verdict"

    assert replacement_candidate.verdict is None
    assert replacement_candidate.awaits_review is True


def test_recording_replacement_verdicts_leaves_first_round_verdicts_untouched() -> None:
    run = _run(_CONTENT)
    run.add_round(
        CandidateRound.FIRST,
        [
            CardProposal(
                front="What starts a connection?", back="A handshake.", quote=_QUOTE
            )
        ],
        _factory(),
    )
    [first_candidate] = run.of_round(CandidateRound.FIRST)
    run.record_verdicts(
        CandidateRound.FIRST,
        [
            CardVerdict(
                ref=first_candidate.ref, grade=ReviewGrade.SOUND, reasoning="clear"
            )
        ],
    )
    first_verdict_before = first_candidate.verdict

    run.add_round(
        CandidateRound.REPLACEMENT,
        [CardProposal(front="Who initiates?", back="The client.", quote=_QUOTE)],
        _factory(),
    )
    [replacement_candidate] = run.of_round(CandidateRound.REPLACEMENT)
    run.record_verdicts(
        CandidateRound.REPLACEMENT,
        [
            CardVerdict(
                ref=replacement_candidate.ref,
                grade=ReviewGrade.STRONG,
                reasoning="excellent",
            )
        ],
    )

    assert first_candidate.verdict == first_verdict_before
    assert first_candidate.accepted is True
    assert replacement_candidate.accepted is True


def test_regeneration_needed_counts_gate_discarded_proposals_toward_the_share() -> None:
    run = _run(_CONTENT)
    run.add_round(
        CandidateRound.FIRST,
        [
            CardProposal(
                front="What starts a connection?", back="A handshake.", quote=_QUOTE
            ),
            CardProposal(
                front="What is missing?", back="Nothing.", quote="never mentioned"
            ),
            CardProposal(
                front="What kind of handshake?", back="Three-way.", quote=_QUOTE
            ),
        ],
        _factory(),
    )
    sound_candidate, ungrounded_candidate, weak_candidate = run.of_round(
        CandidateRound.FIRST
    )
    run.record_verdicts(
        CandidateRound.FIRST,
        [
            CardVerdict(
                ref=sound_candidate.ref, grade=ReviewGrade.SOUND, reasoning="clear"
            ),
            CardVerdict(
                ref=weak_candidate.ref, grade=ReviewGrade.WEAK, reasoning="too vague"
            ),
        ],
    )

    assert ungrounded_candidate.card is not None
    assert ungrounded_candidate.card.discard is not None
    assert ungrounded_candidate.card.discard.reason == DiscardReason.UNGROUNDED
    assert run.regeneration_needed() is True


def test_gaps_and_accepted_example_reflect_the_first_rounds_outcome() -> None:
    run = _run(_CONTENT)
    run.add_round(
        CandidateRound.FIRST,
        [
            CardProposal(
                front="What starts a connection?", back="A handshake.", quote=_QUOTE
            ),
            CardProposal(
                front="What is missing?", back="Nothing.", quote="never mentioned"
            ),
            CardProposal(
                front="What kind of handshake?", back="Three-way.", quote=_QUOTE
            ),
        ],
        _factory(),
    )
    sound_candidate, ungrounded_candidate, weak_candidate = run.of_round(
        CandidateRound.FIRST
    )
    run.record_verdicts(
        CandidateRound.FIRST,
        [
            CardVerdict(
                ref=sound_candidate.ref, grade=ReviewGrade.SOUND, reasoning="clear"
            ),
            CardVerdict(
                ref=weak_candidate.ref, grade=ReviewGrade.WEAK, reasoning="too vague"
            ),
        ],
    )

    assert run.gaps() == [ungrounded_candidate, weak_candidate]
    assert run.accepted_example() == sound_candidate
