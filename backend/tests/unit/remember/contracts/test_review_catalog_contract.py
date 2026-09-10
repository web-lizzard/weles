from collections.abc import Callable
from datetime import UTC, datetime
from typing import NamedTuple
from uuid import uuid4

import pytest

from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.remember.review_catalog import InMemoryReviewCatalog
from domain.distill.card import Card
from domain.distill.note import Note, mint_note
from domain.distill.ports import CardRepository, NoteRepository
from domain.distill.value_objects import (
    Anchor,
    CardSide,
    Discard,
    DiscardReason,
    NoteContent,
    NoteId,
    SessionId,
    TopicSnapshot,
)
from domain.distill.value_objects import CardId as DistillCardId
from domain.remember.ports import ReviewableCard, ReviewCatalog
from domain.remember.value_objects import CardId


class _Catalog(NamedTuple):
    """The port under test plus the seams a contract case seeds through."""

    catalog: ReviewCatalog
    notes: NoteRepository
    cards: CardRepository


def _in_memory() -> _Catalog:
    notes = InMemoryNoteRepository()
    cards = InMemoryCardRepository()
    return _Catalog(InMemoryReviewCatalog(notes, cards), notes, cards)


_IMPLEMENTATIONS: list[Callable[[], _Catalog]] = [_in_memory]


def _sample_note() -> Note:
    return mint_note(
        NoteId(value=uuid4()),
        SessionId(value=uuid4()),
        TopicSnapshot(id=uuid4(), label="Networking"),
        NoteContent(value="Connections are established via a three-way handshake."),
        [],
        datetime.now(UTC),
    )


def _sample_card(
    note_id: NoteId,
    *,
    front: str = "What establishes a connection?",
    back: str = "A three-way handshake.",
    discard: Discard | None = None,
) -> Card:
    return Card(
        id=DistillCardId(value=uuid4()),
        note_id=note_id,
        front=CardSide(value=front),
        back=CardSide(value=back),
        anchor=Anchor(quote="Connections are established via a three-way handshake."),
        discard=discard,
        created_at=datetime.now(UTC),
    )


def _discarded() -> Discard:
    return Discard(
        reason=DiscardReason.UNGROUNDED,
        detail=None,
        discarded_at=datetime.now(UTC),
    )


@pytest.mark.parametrize("make_catalog", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_list_reviewable_renders_a_live_card_under_remember_s_own_card_id(
    make_catalog: Callable[[], _Catalog],
) -> None:
    catalog, notes, cards = make_catalog()
    note = _sample_note()
    card = _sample_card(note.id)
    await notes.save(note)
    await cards.save(card)

    result = await catalog.list_reviewable()

    assert list(result) == [
        ReviewableCard(
            id=CardId(value=card.id.value),
            front=card.front.value,
            back=card.back.value,
        )
    ]


@pytest.mark.parametrize("make_catalog", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_list_reviewable_spans_the_cards_of_every_note(
    make_catalog: Callable[[], _Catalog],
) -> None:
    catalog, notes, cards = make_catalog()
    first_note = _sample_note()
    second_note = _sample_note()
    first_card = _sample_card(first_note.id, front="What is a port?")
    second_card = _sample_card(second_note.id, front="What is a socket?")
    await notes.save(first_note)
    await notes.save(second_note)
    await cards.save(first_card)
    await cards.save(second_card)

    result = await catalog.list_reviewable()

    assert {entry.id for entry in result} == {
        CardId(value=first_card.id.value),
        CardId(value=second_card.id.value),
    }


@pytest.mark.parametrize("make_catalog", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_list_reviewable_omits_a_discarded_card_of_a_note_it_walks(
    make_catalog: Callable[[], _Catalog],
) -> None:
    catalog, notes, cards = make_catalog()
    note = _sample_note()
    live = _sample_card(note.id, front="What is a port?")
    discarded = _sample_card(note.id, front="What is a socket?", discard=_discarded())
    await notes.save(note)
    await cards.save(live)
    await cards.save(discarded)

    result = await catalog.list_reviewable()

    assert [entry.id for entry in result] == [CardId(value=live.id.value)]


@pytest.mark.parametrize("make_catalog", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_get_reviewable_returns_the_card_carrying_that_id(
    make_catalog: Callable[[], _Catalog],
) -> None:
    catalog, notes, cards = make_catalog()
    note = _sample_note()
    wanted = _sample_card(note.id, front="What is a port?")
    other = _sample_card(note.id, front="What is a socket?")
    await notes.save(note)
    await cards.save(wanted)
    await cards.save(other)

    result = await catalog.get_reviewable(CardId(value=wanted.id.value))

    assert result == ReviewableCard(
        id=CardId(value=wanted.id.value),
        front=wanted.front.value,
        back=wanted.back.value,
    )


@pytest.mark.parametrize("make_catalog", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_get_reviewable_offers_a_live_card_but_not_a_discarded_sibling(
    make_catalog: Callable[[], _Catalog],
) -> None:
    catalog, notes, cards = make_catalog()
    note = _sample_note()
    live = _sample_card(note.id, front="What is a port?")
    discarded = _sample_card(note.id, front="What is a socket?", discard=_discarded())
    await notes.save(note)
    await cards.save(live)
    await cards.save(discarded)

    offered = await catalog.get_reviewable(CardId(value=live.id.value))
    withheld = await catalog.get_reviewable(CardId(value=discarded.id.value))

    assert offered is not None
    assert withheld is None


@pytest.mark.parametrize("make_catalog", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_get_reviewable_returns_none_for_an_id_no_note_holds(
    make_catalog: Callable[[], _Catalog],
) -> None:
    catalog, notes, cards = make_catalog()
    note = _sample_note()
    await notes.save(note)
    await cards.save(_sample_card(note.id))

    stocked = await catalog.list_reviewable()
    result = await catalog.get_reviewable(CardId(value=uuid4()))

    assert len(stocked) == 1
    assert result is None
