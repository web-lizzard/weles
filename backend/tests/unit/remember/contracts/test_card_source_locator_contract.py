from collections.abc import Callable
from datetime import UTC, datetime
from typing import NamedTuple
from uuid import uuid4

import pytest

from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.remember.card_source_locator import (
    InMemoryCardSourceLocator,
)
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
from domain.remember.ports import CardSource, CardSourceLocator, SourceBlock, SourceSpan
from domain.remember.value_objects import CardId


class _Locator(NamedTuple):
    """The port under test plus the seams a contract case seeds through."""

    locator: CardSourceLocator
    notes: NoteRepository
    cards: CardRepository


def _in_memory() -> _Locator:
    notes = InMemoryNoteRepository()
    cards = InMemoryCardRepository()
    return _Locator(InMemoryCardSourceLocator(notes, cards), notes, cards)


_IMPLEMENTATIONS: list[Callable[[], _Locator]] = [_in_memory]


def _sample_note(content: str | None = None) -> Note:
    body = (
        content
        if content is not None
        else "Connections are established via a three-way handshake."
    )
    return mint_note(
        NoteId(value=uuid4()),
        SessionId(value=uuid4()),
        TopicSnapshot(id=uuid4(), label="Networking"),
        NoteContent(value=body),
        [],
        datetime.now(UTC),
    )


def _sample_card(
    note_id: NoteId,
    *,
    quote: str = "Connections are established via a three-way handshake.",
    discard: Discard | None = None,
) -> Card:
    return Card(
        id=DistillCardId(value=uuid4()),
        note_id=note_id,
        front=CardSide(value="What establishes a connection?"),
        back=CardSide(value="A three-way handshake."),
        anchor=Anchor(quote=quote),
        discard=discard,
        created_at=datetime.now(UTC),
    )


def _discarded() -> Discard:
    return Discard(
        reason=DiscardReason.UNGROUNDED,
        detail=None,
        discarded_at=datetime.now(UTC),
    )


@pytest.mark.parametrize("make_locator", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_locate_returns_every_block_and_exact_span_when_anchor_matches(
    make_locator: Callable[[], _Locator],
) -> None:
    locator, notes, cards = make_locator()
    note_body = (
        "Lead paragraph.\n\n"
        "Connections are established via a three-way handshake.\n\n"
        "Tail."
    )
    note = _sample_note(note_body)
    card = _sample_card(note.id)
    await notes.save(note)
    await cards.save(card)

    result = await locator.locate(CardId(value=card.id.value))

    assert result == CardSource(
        blocks=[
            SourceBlock(index=0, text="Lead paragraph."),
            SourceBlock(
                index=1,
                text="Connections are established via a three-way handshake.",
            ),
            SourceBlock(index=2, text="Tail."),
        ],
        span=SourceSpan(block_index=1, start=0, end=54),
    )


@pytest.mark.parametrize("make_locator", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_locate_returns_none_for_a_card_id_no_repository_holds(
    make_locator: Callable[[], _Locator],
) -> None:
    locator, notes, cards = make_locator()
    note = _sample_note()
    card = _sample_card(note.id)
    await notes.save(note)
    await cards.save(card)

    result = await locator.locate(CardId(value=uuid4()))

    assert result is None


@pytest.mark.parametrize("make_locator", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_locate_returns_none_for_a_discarded_card(
    make_locator: Callable[[], _Locator],
) -> None:
    locator, notes, cards = make_locator()
    note = _sample_note()
    card = _sample_card(note.id, discard=_discarded())
    await notes.save(note)
    await cards.save(card)

    result = await locator.locate(CardId(value=card.id.value))

    assert result is None


@pytest.mark.parametrize("make_locator", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_locate_returns_none_when_the_note_behind_the_card_is_missing(
    make_locator: Callable[[], _Locator],
) -> None:
    locator, _notes, cards = make_locator()
    note = _sample_note()
    card = _sample_card(note.id)
    await cards.save(card)

    result = await locator.locate(CardId(value=card.id.value))

    assert result is None


@pytest.mark.parametrize("make_locator", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_locate_returns_none_when_the_note_no_longer_contains_the_card_quote(
    make_locator: Callable[[], _Locator],
) -> None:
    locator, notes, cards = make_locator()
    note = _sample_note()
    card = _sample_card(note.id)
    await notes.save(note)
    await cards.save(card)
    await notes.save(
        note.model_copy(
            update={
                "content": NoteContent(
                    value="The note was rewritten without the quote."
                )
            }
        )
    )

    result = await locator.locate(CardId(value=card.id.value))

    assert result is None
