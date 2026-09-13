from datetime import UTC, datetime
from uuid import uuid4

from domain.distill.card_factory import CardFactory
from domain.distill.note import mint_note
from domain.distill.note_document import NoteDocument
from domain.distill.regeneration import RegenerationPolicy, ThresholdTier
from domain.distill.run import CandidateRound, DistillRun
from domain.distill.value_objects import (
    CardLengthPolicy,
    CardProposal,
    DiscardReason,
    NoteContent,
    NoteId,
    SessionId,
    TopicSnapshot,
)

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


def test_later_rounds_continue_the_ref_sequence_in_proposal_order() -> None:
    run = _run(_CONTENT)
    factory = _factory()

    run.add_round(
        CandidateRound.FIRST,
        [
            CardProposal(
                front="What starts a connection?",
                back="A handshake.",
                quote=_QUOTE,
            ),
            CardProposal(
                front="What kind of handshake?",
                back="Three-way.",
                quote=_QUOTE,
            ),
        ],
        factory,
    )
    run.add_round(
        CandidateRound.REPLACEMENT,
        [
            CardProposal(front="Who initiates?", back="The client.", quote=_QUOTE),
        ],
        factory,
    )

    first = run.of_round(CandidateRound.FIRST)
    replacement = run.of_round(CandidateRound.REPLACEMENT)

    assert [candidate.ref.value for candidate in first] == ["c1", "c2"]
    assert [candidate.ref.value for candidate in replacement] == ["c3"]
    assert [candidate.round for candidate in first] == [
        CandidateRound.FIRST,
        CandidateRound.FIRST,
    ]
    assert replacement[0].round is CandidateRound.REPLACEMENT


def test_only_a_live_grounded_card_awaits_review() -> None:
    run = _run(_CONTENT)

    run.add_round(
        CandidateRound.FIRST,
        [
            CardProposal(
                front="What starts a connection?",
                back="A handshake.",
                quote=_QUOTE,
            ),
            CardProposal(
                front="What is missing?",
                back="Nothing in the note.",
                quote="never mentioned",
            ),
            CardProposal(front="a" * 31, back="A handshake.", quote=_QUOTE),
        ],
        _factory(),
    )

    live, ungrounded, oversized = run.of_round(CandidateRound.FIRST)

    assert live.awaits_review is True
    assert live.failure is None
    assert live.card is not None
    assert live.card.discard is None
    assert live.card.note_id == run.note.id

    assert ungrounded.awaits_review is False
    assert ungrounded.card is not None
    assert ungrounded.card.discard is not None
    assert ungrounded.card.discard.reason == DiscardReason.UNGROUNDED
    assert ungrounded.failure == DiscardReason.UNGROUNDED

    assert oversized.awaits_review is False
    assert oversized.card is not None
    assert oversized.card.discard is not None
    assert oversized.card.discard.reason == DiscardReason.OVERSIZED
    assert oversized.failure == f"{DiscardReason.OVERSIZED}: front exceeds front_max=30"

    assert run.awaiting_review(CandidateRound.FIRST) == [live]
    assert run.awaiting_review(CandidateRound.REPLACEMENT) == []
    assert run.cards() == [live.card, ungrounded.card, oversized.card]


def test_an_unmintable_proposal_is_kept_without_a_card() -> None:
    run = _run(_CONTENT)

    run.add_round(
        CandidateRound.FIRST,
        [CardProposal(front="", back="A handshake.", quote=_QUOTE)],
        _factory(),
    )

    [candidate] = run.of_round(CandidateRound.FIRST)

    assert candidate.card is None
    assert candidate.awaits_review is False
    assert candidate.failure == "could not become a card"
    assert run.cards() == []
    assert run.awaiting_review(CandidateRound.FIRST) == []
