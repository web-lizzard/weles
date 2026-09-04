from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import pytest

from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from domain.distill.card import Card
from domain.distill.ports import CardRepository
from domain.distill.value_objects import (
    Anchor,
    CardId,
    CardSide,
    Discard,
    DiscardReason,
    NoteId,
)

_IMPLEMENTATIONS: list[Callable[[], CardRepository]] = [
    cast(Callable[[], CardRepository], InMemoryCardRepository),
]


def _sample_card(note_id: NoteId, discard: Discard | None = None) -> Card:
    return Card(
        id=CardId(value=uuid4()),
        note_id=note_id,
        front=CardSide(value="What establishes a connection?"),
        back=CardSide(value="A three-way handshake."),
        anchor=Anchor(quote="Connections are established via a three-way handshake."),
        discard=discard,
        created_at=datetime.now(UTC),
    )


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_save_then_list_by_note_returns_the_saved_card(
    make_repository: Callable[[], CardRepository],
) -> None:
    repository = make_repository()
    note_id = NoteId(value=uuid4())
    card = _sample_card(note_id)

    await repository.save(card)
    result = await repository.list_by_note(note_id)

    assert result == [card]


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_list_by_note_returns_empty_for_a_note_with_no_cards(
    make_repository: Callable[[], CardRepository],
) -> None:
    repository = make_repository()
    await repository.save(_sample_card(NoteId(value=uuid4())))

    result = await repository.list_by_note(NoteId(value=uuid4()))

    assert result == []


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_list_by_note_includes_discarded_cards(
    make_repository: Callable[[], CardRepository],
) -> None:
    repository = make_repository()
    note_id = NoteId(value=uuid4())
    live = _sample_card(note_id)
    discarded = _sample_card(
        note_id,
        discard=Discard(
            reason=DiscardReason.UNGROUNDED,
            detail=None,
            discarded_at=datetime.now(UTC),
        ),
    )

    await repository.save(live)
    await repository.save(discarded)
    result = await repository.list_by_note(note_id)

    assert result == [live, discarded] or result == [discarded, live]


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_second_save_with_same_id_overwrites(
    make_repository: Callable[[], CardRepository],
) -> None:
    repository = make_repository()
    note_id = NoteId(value=uuid4())
    original = _sample_card(note_id)
    updated = original.model_copy(
        update={
            "discard": Discard(
                reason=DiscardReason.OVERSIZED,
                detail="front exceeds front_max=10",
                discarded_at=datetime.now(UTC),
            )
        }
    )

    await repository.save(original)
    await repository.save(updated)
    result = await repository.list_by_note(note_id)

    assert result == [updated]
