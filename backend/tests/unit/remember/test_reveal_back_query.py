from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from application.remember.queries.reveal_back import RevealBackQuery
from domain.remember.exceptions import (
    CardNotInSittingError,
    CardNotReviewableError,
    SittingNotFoundError,
)
from domain.remember.ports import ReviewableCard
from domain.remember.sitting import Sitting
from domain.remember.value_objects import CardId, ShowingLimit, SittingId


def _card_id() -> CardId:
    return CardId(value=uuid4())


def _reviewable(
    card_id: CardId | None = None,
    *,
    front: str = "What is UDP?",
    back: str = "Connectionless datagrams.",
) -> ReviewableCard:
    return ReviewableCard(id=card_id or _card_id(), front=front, back=back)


def _open_sitting(*cards: ReviewableCard) -> Sitting:
    return Sitting.open(
        frozenset(card.id for card in cards),
        datetime.now(UTC),
        ShowingLimit(value=2),
    )


class _Catalog:
    def __init__(self, cards: Sequence[ReviewableCard]) -> None:
        self._cards: dict[CardId, ReviewableCard] = {card.id: card for card in cards}

    async def list_reviewable(self) -> Sequence[ReviewableCard]:
        return list(self._cards.values())

    async def get_reviewable(self, card_id: CardId) -> ReviewableCard | None:
        return self._cards.get(card_id)

    def remove(self, card_id: CardId) -> None:
        _ = self._cards.pop(card_id, None)


class _SittingRepository:
    def __init__(self) -> None:
        self._sittings: dict[SittingId, Sitting] = {}

    async def save(self, sitting: Sitting) -> None:
        self._sittings[sitting.id] = sitting

    async def get(self, sitting_id: SittingId) -> Sitting | None:
        return self._sittings.get(sitting_id)


def _query(
    *,
    _sitting: Sitting,
    catalog: _Catalog,
) -> tuple[RevealBackQuery, _SittingRepository]:
    sittings = _SittingRepository()
    return RevealBackQuery(sittings, catalog), sittings


async def _saved_query(
    *,
    sitting: Sitting,
    catalog: _Catalog,
) -> tuple[RevealBackQuery, Sitting]:
    query, sittings = _query(_sitting=sitting, catalog=catalog)
    await sittings.save(sitting)
    return query, sitting


async def test_a_sitting_member_returns_its_front_and_back() -> None:
    card = _reviewable(front="Name three layers", back="Physical, data link, network.")
    sitting = _open_sitting(card)
    catalog = _Catalog([card])
    query, _ = await _saved_query(sitting=sitting, catalog=catalog)

    result = await query.handle(sitting.id, card.id)

    assert result.sitting_id == sitting.id.value
    assert result.card_id == card.id.value
    assert result.front == "Name three layers"
    assert result.back == "Physical, data link, network."


async def test_an_unknown_sitting_raises_sitting_not_found() -> None:
    card = _reviewable()
    catalog = _Catalog([card])
    query, _ = _query(_sitting=_open_sitting(card), catalog=catalog)

    with pytest.raises(SittingNotFoundError):
        _ = await query.handle(SittingId.new(), card.id)


async def test_a_card_outside_the_sitting_raises_card_not_in_sitting() -> None:
    member = _reviewable()
    outsider = _reviewable()
    sitting = _open_sitting(member)
    catalog = _Catalog([member, outsider])
    query, _ = await _saved_query(sitting=sitting, catalog=catalog)

    with pytest.raises(CardNotInSittingError):
        _ = await query.handle(sitting.id, outsider.id)


async def test_a_discarded_card_raises_card_not_reviewable() -> None:
    card = _reviewable()
    sitting = _open_sitting(card)
    catalog = _Catalog([card])
    catalog.remove(card.id)
    query, _ = await _saved_query(sitting=sitting, catalog=catalog)

    with pytest.raises(CardNotReviewableError):
        _ = await query.handle(sitting.id, card.id)


async def test_reveal_does_not_require_the_card_to_be_in_front() -> None:
    first = _reviewable(front="First front", back="First back")
    second = _reviewable(front="Second front", back="Second back")
    sitting = _open_sitting(first, second)
    catalog = _Catalog([first, second])
    query, _ = await _saved_query(sitting=sitting, catalog=catalog)
    in_front = sitting.next_card(frozenset({first.id, second.id}), events=[])
    assert in_front is not None
    other = second if in_front == first.id else first

    result = await query.handle(sitting.id, other.id)

    assert result.card_id == other.id.value
    assert result.front == other.front
    assert result.back == other.back
