from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from domain.distill.card import Card
from domain.distill.card_factory import CardFactory
from domain.distill.note import Note
from domain.distill.note_document import NoteDocument
from domain.distill.regeneration import RegenerationPolicy
from domain.distill.value_objects import (
    Anchor,
    AnchorResolution,
    CandidateRef,
    CardProposal,
    CardSide,
    CardVerdict,
    Discard,
    DiscardReason,
    DistillPhase,
    DuplicateGroup,
    ReviewGrade,
)
from domain.exceptions import CoreException


class CandidateRound(StrEnum):
    """Which generation produced a candidate. Merge's tie rule reads it."""

    FIRST = "first"
    REPLACEMENT = "replacement"


class Candidate(BaseModel):
    """One proposal as the run tracks it, from proposal to its last verdict.

    `card` is `None` when the proposal could not become a card at all (empty
    or identical sides); such a candidate still counts toward its round's
    share. A minted card already carries a gate discard when its anchor did
    not resolve or it breached the length policy — that candidate never reaches
    review. `verdict` is set by the review phase that judged it, and only by
    that one.
    """

    ref: CandidateRef
    round: CandidateRound
    proposal: CardProposal
    card: Card | None
    verdict: CardVerdict | None = None

    @property
    def awaits_review(self) -> bool:
        """Minted, not discarded at the gates, and not yet judged."""
        return (
            self.card is not None and self.card.discard is None and self.verdict is None
        )

    @property
    def accepted(self) -> bool:
        """Judged, with a grade that passes, and not discarded since."""
        return (
            self.verdict is not None
            and self.verdict.grade.passes
            and self.card is not None
            and self.card.discard is None
        )

    @property
    def failure(self) -> str | None:
        """Why this candidate did not survive, as regeneration is told it: the
        review's reasoning, the gate's discard reason, or that the proposal
        could not become a card. `None` for a candidate still standing."""
        if self.card is None:
            return "could not become a card"
        discard = self.card.discard
        if discard is None:
            return None
        if discard.detail is not None:
            return f"{discard.reason}: {discard.detail}"
        return str(discard.reason)


class DistillRun(BaseModel):
    """What one card-generation run carries: the note, its document, the
    policy that decides whether to regenerate, and every candidate so far.

    The machine's context. Transient — built by the command, walked, read, and
    dropped; `phase` exists only so the machine has somewhere to hold it.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    note: Note
    document: NoteDocument
    policy: RegenerationPolicy
    phase: DistillPhase = DistillPhase.GENERATING
    candidates: list[Candidate] = Field(default_factory=list)

    def add_round(
        self,
        round: CandidateRound,
        proposals: Sequence[CardProposal],
        card_factory: CardFactory,
    ) -> None:
        """Append one candidate per proposal, in order, under refs continuing
        the run's sequence. Each proposal is minted through `card_factory` with
        its anchor resolved against `document`, so gate discards are set on the
        way in; a proposal that cannot become a card is kept with `card=None`.

        Called once per round — a second call for a round already present is
        a mistake of the flow, which the graph's shape already rules out.
        """
        for proposal in proposals:
            ref = CandidateRef(value=f"c{len(self.candidates) + 1}")
            card: Card | None
            try:
                front = CardSide(value=proposal.front)
                back = CardSide(value=proposal.back)
                anchor = Anchor(quote=proposal.quote)
                location = self.document.locate(anchor)
                resolution = (
                    AnchorResolution.RESOLVED
                    if location is not None
                    else AnchorResolution.UNRESOLVED
                )
                card = card_factory.mint(self.note.id, front, back, anchor, resolution)
            except CoreException:
                card = None
            self.candidates.append(
                Candidate(ref=ref, round=round, proposal=proposal, card=card)
            )

    def record_verdicts(
        self, round: CandidateRound, verdicts: Sequence[CardVerdict]
    ) -> None:
        """Set each verdict on the candidate of `round` its ref names, and
        discard `LOW_QUALITY`, with the verdict's reasoning as detail, every
        card whose grade does not pass. First-round verdicts are never
        overwritten by a replacement review, because it passes only its own
        round."""
        verdict_by_ref = {verdict.ref: verdict for verdict in verdicts}
        for candidate in self.of_round(round):
            if not candidate.awaits_review:
                continue
            assert candidate.card is not None
            verdict = verdict_by_ref.get(candidate.ref) or CardVerdict(
                ref=candidate.ref, grade=ReviewGrade.POOR, reasoning="no verdict"
            )
            candidate.verdict = verdict
            if not verdict.grade.passes:
                candidate.card.discard = Discard(
                    reason=DiscardReason.LOW_QUALITY,
                    detail=verdict.reasoning,
                    discarded_at=datetime.now(UTC),
                )

    def discard_duplicates(self, groups: Sequence[DuplicateGroup]) -> None:
        """In each group keep the member with the better grade — a replacement
        over a first-round card on equal grades — and discard the rest
        `DUPLICATE`, with the group's reasoning as detail. Only members of
        `merge_pool` are touched."""
        _ = groups
        ...

    def of_round(self, round: CandidateRound) -> list[Candidate]:
        """Every candidate of one round, in proposal order."""
        return [candidate for candidate in self.candidates if candidate.round is round]

    def awaiting_review(self, round: CandidateRound) -> list[Candidate]:
        """The round's candidates a review phase judges."""
        return [
            candidate for candidate in self.of_round(round) if candidate.awaits_review
        ]

    def regeneration_needed(self) -> bool:
        """The first round's accepted share falls below the policy's threshold
        for this note, counted over every first-round candidate."""
        first_round = self.of_round(CandidateRound.FIRST)
        accepted = sum(1 for candidate in first_round if candidate.accepted)
        return self.policy.regenerate(self.note.content, accepted, len(first_round))

    def gaps(self) -> list[Candidate]:
        """First-round candidates that did not survive — what regeneration
        replaces, each with its `failure`."""
        return [
            candidate
            for candidate in self.of_round(CandidateRound.FIRST)
            if candidate.failure is not None
        ]

    def accepted_example(self) -> Candidate | None:
        """One accepted first-round candidate to show regeneration, if any."""
        for candidate in self.of_round(CandidateRound.FIRST):
            if candidate.accepted:
                return candidate
        return None

    def merge_pool(self) -> list[Candidate]:
        """Candidates accepted by either review — what merge judges."""
        ...

    def cards(self) -> list[Card]:
        """Every minted card, surviving or discarded, for the command to
        persist once the run has finished."""
        return [
            candidate.card
            for candidate in self.candidates
            if candidate.card is not None
        ]


class CardsProposed(BaseModel, frozen=True):
    """A generation phase's answer. Both generation phases answer with it;
    which round it makes is the phase's decision, not the event's."""

    kind: Literal["cards_proposed"] = "cards_proposed"
    proposals: list[CardProposal]


class CardsReviewed(BaseModel, frozen=True):
    """A review phase's answer. Empty exactly when there was nothing to judge
    and the phase answered without a model."""

    kind: Literal["cards_reviewed"] = "cards_reviewed"
    verdicts: list[CardVerdict]


class DuplicatesFound(BaseModel, frozen=True):
    """Merge's answer. Empty when there were fewer than two cards to compare."""

    kind: Literal["duplicates_found"] = "duplicates_found"
    groups: list[DuplicateGroup]


type DistillEvent = Annotated[
    CardsProposed | CardsReviewed | DuplicatesFound,
    Field(discriminator="kind"),
]
"""Everything a distill phase answers with, model or not. Each member is also
a phase's declared `output`, so what the model returns is applied as is."""
