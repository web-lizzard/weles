from datetime import UTC, datetime
from uuid import uuid4

import pytest

from domain.distill.card import Card
from domain.distill.exceptions import IdenticalCardSidesError
from domain.distill.value_objects import (
    Anchor,
    CardId,
    CardSide,
    NoteId,
)
from domain.shared.identity.model import UserId


def _build_card(front: str, back: str) -> Card:
    return Card(
        id=CardId(value=uuid4()),
        owner_id=UserId.new(),
        note_id=NoteId(value=uuid4()),
        front=CardSide(value=front),
        back=CardSide(value=back),
        anchor=Anchor(quote="Connections are established via a three-way handshake."),
        discard=None,
        created_at=datetime.now(UTC),
    )


def test_a_card_whose_sides_differ_is_constructed() -> None:
    card = _build_card("What establishes a connection?", "A three-way handshake.")

    assert card.front.value == "What establishes a connection?"
    assert card.back.value == "A three-way handshake."


@pytest.mark.parametrize(
    ("front", "back"),
    [
        pytest.param(
            "A three-way handshake.",
            "A three-way handshake.",
            id="exactly_equal",
        ),
        pytest.param(
            "A three-way handshake.",
            "a THREE-way Handshake.",
            id="equal_ignoring_case",
        ),
    ],
)
def test_a_card_whose_sides_are_the_same_is_rejected(front: str, back: str) -> None:
    with pytest.raises(IdenticalCardSidesError):
        _ = _build_card(front, back)
