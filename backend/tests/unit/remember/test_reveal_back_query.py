import pytest
from integration.support.in_memory_remember import InMemoryRememberComposition

from domain.remember.exceptions import (
    CardNotInSittingError,
    CardNotReviewableError,
    SittingNotFoundError,
)
from domain.remember.value_objects import SittingId

from .conftest import open_sitting, reviewable


async def test_a_sitting_member_returns_its_front_and_back(
    composition: InMemoryRememberComposition,
) -> None:
    card = await reviewable(
        composition, front="Name three layers", back="Physical, data link, network."
    )
    sitting = open_sitting(card)
    await composition.sittings.save(sitting)

    result = await composition.reveal_back().handle(sitting.id, card.id)

    assert result.sitting_id == sitting.id.value
    assert result.card_id == card.id.value
    assert result.front == "Name three layers"
    assert result.back == "Physical, data link, network."


async def test_an_unknown_sitting_raises_sitting_not_found(
    composition: InMemoryRememberComposition,
) -> None:
    card = await reviewable(composition)

    with pytest.raises(SittingNotFoundError):
        _ = await composition.reveal_back().handle(SittingId.new(), card.id)


async def test_a_card_outside_the_sitting_raises_card_not_in_sitting(
    composition: InMemoryRememberComposition,
) -> None:
    member = await reviewable(composition)
    outsider = await reviewable(composition)
    sitting = open_sitting(member)
    await composition.sittings.save(sitting)

    with pytest.raises(CardNotInSittingError):
        _ = await composition.reveal_back().handle(sitting.id, outsider.id)


async def test_a_discarded_card_raises_card_not_reviewable(
    composition: InMemoryRememberComposition,
) -> None:
    card = await reviewable(composition, discarded=True)
    sitting = open_sitting(card)
    await composition.sittings.save(sitting)

    with pytest.raises(CardNotReviewableError):
        _ = await composition.reveal_back().handle(sitting.id, card.id)


async def test_reveal_does_not_require_the_card_to_be_in_front(
    composition: InMemoryRememberComposition,
) -> None:
    first = await reviewable(composition, front="First front", back="First back")
    second = await reviewable(composition, front="Second front", back="Second back")
    sitting = open_sitting(first, second)
    await composition.sittings.save(sitting)
    in_front = sitting.next_card(frozenset({first.id, second.id}), events=[])
    assert in_front is not None
    other = second if in_front == first.id else first

    result = await composition.reveal_back().handle(sitting.id, other.id)

    assert result.card_id == other.id.value
    assert result.front == other.front
    assert result.back == other.back
