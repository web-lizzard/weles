from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from application.remember.dto import PresentedCardDTO
from application.remember.queries.current_card import CurrentCardQuery
from domain.remember.exceptions import SittingNotFoundError
from domain.remember.ports import ReviewableCard
from domain.remember.review_event import ReviewEvent
from domain.remember.sitting import Sitting
from domain.remember.value_objects import CardId, Grade, ShowingLimit, SittingId


def _card_id() -> CardId:
    return CardId(value=uuid4())


def _reviewable(
    card_id: CardId | None = None,
    *,
    front: str = "What is ICMP?",
) -> ReviewableCard:
    return ReviewableCard(
        id=card_id or _card_id(), front=front, back="Ping and errors."
    )


def _open_sitting(*cards: ReviewableCard) -> Sitting:
    return Sitting.open(
        frozenset(card.id for card in cards),
        datetime.now(UTC),
        ShowingLimit(value=2),
    )


def _event(
    card_id: CardId,
    sitting_id: SittingId,
    grade: Grade,
) -> ReviewEvent:
    return ReviewEvent(
        card_id=card_id,
        reviewed_at=datetime.now(UTC),
        grade=grade,
        sitting_id=sitting_id,
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


class _ReviewEventStore:
    def __init__(self, events: Sequence[ReviewEvent] = ()) -> None:
        self._events: list[ReviewEvent] = list(events)

    async def save(self, event: ReviewEvent) -> None:
        self._events.append(event)

    async def list_by_card(self, card_id: CardId) -> Sequence[ReviewEvent]:
        del card_id
        return ()

    async def list_by_sitting(self, sitting_id: SittingId) -> Sequence[ReviewEvent]:
        return sorted(
            (event for event in self._events if event.sitting_id == sitting_id),
            key=lambda event: event.reviewed_at,
        )


def _query(
    *,
    _sitting: Sitting,
    catalog: _Catalog,
    events: Sequence[ReviewEvent] = (),
) -> tuple[CurrentCardQuery, _SittingRepository]:
    sittings = _SittingRepository()
    return CurrentCardQuery(
        sittings,
        _ReviewEventStore(events),
        catalog,
    ), sittings


async def _saved_query(
    *,
    sitting: Sitting,
    catalog: _Catalog,
    events: Sequence[ReviewEvent] = (),
) -> tuple[CurrentCardQuery, Sitting]:
    query, sittings = _query(_sitting=sitting, catalog=catalog, events=events)
    await sittings.save(sitting)
    return query, sitting


async def test_the_current_card_is_the_next_draw_from_the_sitting_log() -> None:
    shown = _reviewable(front="Shown already")
    unshown = _reviewable(front="Still waiting")
    sitting = _open_sitting(shown, unshown)
    events = (_event(shown.id, sitting.id, Grade.FORGOT),)
    catalog = _Catalog([shown, unshown])
    query, _ = await _saved_query(sitting=sitting, catalog=catalog, events=events)
    expected = sitting.next_card(
        sitting.visible(frozenset({shown.id, unshown.id})),
        events,
    )
    assert expected is not None

    result = await query.handle(sitting.id)

    assert isinstance(result, PresentedCardDTO)
    assert result.sitting_id == sitting.id.value
    assert result.card_id == expected.value
    assert result.front == unshown.front
    assert result.sitting_complete is False


async def test_an_unknown_sitting_raises_sitting_not_found() -> None:
    card = _reviewable()
    catalog = _Catalog([card])
    query, _ = _query(_sitting=_open_sitting(card), catalog=catalog)

    with pytest.raises(SittingNotFoundError):
        _ = await query.handle(SittingId.new())


async def test_two_consecutive_reads_return_the_same_card() -> None:
    card = _reviewable(front="Stable pick")
    sitting = _open_sitting(card)
    catalog = _Catalog([card])
    query, _ = await _saved_query(sitting=sitting, catalog=catalog)

    first = await query.handle(sitting.id)
    second = await query.handle(sitting.id)

    assert first.card_id == second.card_id
    assert first.front == second.front == "Stable pick"
    assert first.sitting_complete is False
    assert second.sitting_complete is False


async def test_a_discarded_member_is_excluded_from_the_draw() -> None:
    kept = _reviewable(front="Still reviewable")
    dropped = _reviewable(front="Discarded elsewhere")
    sitting = _open_sitting(kept, dropped)
    catalog = _Catalog([kept, dropped])
    catalog.remove(dropped.id)
    query, _ = await _saved_query(sitting=sitting, catalog=catalog)

    result = await query.handle(sitting.id)

    assert result.card_id == kept.id.value
    assert result.front == "Still reviewable"
    assert result.sitting_complete is False


async def test_a_finished_sitting_reports_completion_through_the_dto() -> None:
    """Phase 6 contract: sitting_complete comes from is_finished on the DTO."""
    card = _reviewable(front="Finished by grade")
    sitting = _open_sitting(card)
    events = (_event(card.id, sitting.id, Grade.GOOD),)
    catalog = _Catalog([card])
    query, _ = await _saved_query(sitting=sitting, catalog=catalog, events=events)

    result = await query.handle(sitting.id)

    assert isinstance(result, PresentedCardDTO)
    assert result.sitting_complete is True
