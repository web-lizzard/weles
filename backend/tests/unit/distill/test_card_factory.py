from datetime import UTC
from uuid import uuid4

from domain.distill.card_factory import CardFactory
from domain.distill.value_objects import (
    Anchor,
    AnchorResolution,
    CardLengthPolicy,
    CardSide,
    DiscardReason,
    NoteId,
)

_QUOTE = "Connections are established via a three-way handshake."


def _factory() -> CardFactory:
    return CardFactory(CardLengthPolicy(front_max=30, back_max=40))


def test_a_resolved_proposal_within_the_policy_mints_a_live_card() -> None:
    note_id = NoteId(value=uuid4())

    card = _factory().mint(
        note_id,
        CardSide(value="What establishes a connection?"),
        CardSide(value="A three-way handshake."),
        Anchor(quote=_QUOTE),
        AnchorResolution.RESOLVED,
    )

    assert card.discard is None
    assert card.note_id == note_id
    assert card.anchor.quote == _QUOTE


def test_an_unresolved_anchor_mints_a_discard_keeping_the_claimed_quote() -> None:
    card = _factory().mint(
        NoteId(value=uuid4()),
        CardSide(value="What establishes a connection?"),
        CardSide(value="A three-way handshake."),
        Anchor(quote=_QUOTE),
        AnchorResolution.UNRESOLVED,
    )

    assert card.discard is not None
    assert card.discard.reason == DiscardReason.UNGROUNDED
    assert card.discard.detail is None
    assert card.discard.discarded_at.tzinfo is UTC
    assert card.anchor.quote == _QUOTE


def test_a_side_past_the_policy_bound_mints_a_discarded_card_naming_the_side() -> None:
    card = _factory().mint(
        NoteId(value=uuid4()),
        CardSide(value="a" * 31),
        CardSide(value="A three-way handshake."),
        Anchor(quote=_QUOTE),
        AnchorResolution.RESOLVED,
    )

    assert card.discard is not None
    assert card.discard.reason == DiscardReason.OVERSIZED
    assert card.discard.detail == "front exceeds front_max=30"


def test_grounding_is_judged_before_length_when_a_proposal_breaches_both() -> None:
    card = _factory().mint(
        NoteId(value=uuid4()),
        CardSide(value="a" * 31),
        CardSide(value="A three-way handshake."),
        Anchor(quote=_QUOTE),
        AnchorResolution.UNRESOLVED,
    )

    assert card.discard is not None
    assert card.discard.reason == DiscardReason.UNGROUNDED
