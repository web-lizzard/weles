from datetime import UTC, datetime
from typing import NamedTuple
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.remember.review_catalog import InMemoryReviewCatalog
from adapters.out.sqlalchemy.distill.card_repository import SqlAlchemyCardRepository
from adapters.out.sqlalchemy.distill.note_repository import SqlAlchemyNoteRepository
from adapters.out.sqlalchemy.engine import create_session_factory
from adapters.out.sqlalchemy.remember.review_catalog import SqlAlchemyReviewCatalog
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
from domain.shared.identity.model import UserId

_OWNER = UserId.new()


class _CommittingNoteRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def save(self, note: Note) -> None:
        async with self._session_factory() as db_session:
            await SqlAlchemyNoteRepository(db_session).save(note)
            await db_session.commit()

    async def get(self, note_id: NoteId) -> Note | None:
        async with self._session_factory() as db_session:
            return await SqlAlchemyNoteRepository(db_session).get(note_id)

    async def list_all(self) -> list[Note]:
        async with self._session_factory() as db_session:
            return await SqlAlchemyNoteRepository(db_session).list_all()


class _CommittingCardRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def save(self, card: Card) -> None:
        async with self._session_factory() as db_session:
            await SqlAlchemyCardRepository(db_session).save(card)
            await db_session.commit()

    async def get(self, card_id: DistillCardId) -> Card | None:
        async with self._session_factory() as db_session:
            return await SqlAlchemyCardRepository(db_session).get(card_id)

    async def list_by_note(self, note_id: NoteId) -> list[Card]:
        async with self._session_factory() as db_session:
            return await SqlAlchemyCardRepository(db_session).list_by_note(note_id)


class _Catalog(NamedTuple):
    """The port under test plus the seams a contract case seeds through."""

    catalog: ReviewCatalog
    notes: NoteRepository
    cards: CardRepository


@pytest.fixture(
    params=["in_memory", pytest.param("postgres", marks=pytest.mark.postgres)]
)
def catalog_fixture(request: pytest.FixtureRequest) -> _Catalog:
    if request.param == "in_memory":  # pyright: ignore[reportAny]
        notes = InMemoryNoteRepository()
        cards = InMemoryCardRepository()
        return _Catalog(InMemoryReviewCatalog(notes, cards), notes, cards)
    engine: AsyncEngine = request.getfixturevalue("engine")  # pyright: ignore[reportAny]
    session_factory = create_session_factory(engine)
    notes = _CommittingNoteRepository(session_factory)
    cards = _CommittingCardRepository(session_factory)
    return _Catalog(SqlAlchemyReviewCatalog(session_factory), notes, cards)


def _sample_note() -> Note:
    return mint_note(
        UserId.new(),
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
        owner_id=UserId.new(),
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


async def test_list_reviewable_renders_a_live_card_under_remember_s_own_card_id(
    catalog_fixture: _Catalog,
) -> None:
    catalog, notes, cards = catalog_fixture
    note = _sample_note()
    card = _sample_card(note.id)
    await notes.save(note)
    await cards.save(card)

    result = await catalog.list_reviewable(_OWNER)

    assert list(result) == [
        ReviewableCard(
            id=CardId(value=card.id.value),
            front=card.front.value,
            back=card.back.value,
        )
    ]


async def test_list_reviewable_spans_the_cards_of_every_note(
    catalog_fixture: _Catalog,
) -> None:
    catalog, notes, cards = catalog_fixture
    first_note = _sample_note()
    second_note = _sample_note()
    first_card = _sample_card(first_note.id, front="What is a port?")
    second_card = _sample_card(second_note.id, front="What is a socket?")
    await notes.save(first_note)
    await notes.save(second_note)
    await cards.save(first_card)
    await cards.save(second_card)

    result = await catalog.list_reviewable(_OWNER)

    assert {entry.id for entry in result} == {
        CardId(value=first_card.id.value),
        CardId(value=second_card.id.value),
    }


async def test_list_reviewable_omits_a_discarded_card_of_a_note_it_walks(
    catalog_fixture: _Catalog,
) -> None:
    catalog, notes, cards = catalog_fixture
    note = _sample_note()
    live = _sample_card(note.id, front="What is a port?")
    discarded = _sample_card(note.id, front="What is a socket?", discard=_discarded())
    await notes.save(note)
    await cards.save(live)
    await cards.save(discarded)

    result = await catalog.list_reviewable(_OWNER)

    assert [entry.id for entry in result] == [CardId(value=live.id.value)]


async def test_get_reviewable_returns_the_card_carrying_that_id(
    catalog_fixture: _Catalog,
) -> None:
    catalog, notes, cards = catalog_fixture
    note = _sample_note()
    wanted = _sample_card(note.id, front="What is a port?")
    other = _sample_card(note.id, front="What is a socket?")
    await notes.save(note)
    await cards.save(wanted)
    await cards.save(other)

    result = await catalog.get_reviewable(_OWNER, CardId(value=wanted.id.value))

    assert result == ReviewableCard(
        id=CardId(value=wanted.id.value),
        front=wanted.front.value,
        back=wanted.back.value,
    )


async def test_get_reviewable_offers_a_live_card_but_not_a_discarded_sibling(
    catalog_fixture: _Catalog,
) -> None:
    catalog, notes, cards = catalog_fixture
    note = _sample_note()
    live = _sample_card(note.id, front="What is a port?")
    discarded = _sample_card(note.id, front="What is a socket?", discard=_discarded())
    await notes.save(note)
    await cards.save(live)
    await cards.save(discarded)

    offered = await catalog.get_reviewable(_OWNER, CardId(value=live.id.value))
    withheld = await catalog.get_reviewable(_OWNER, CardId(value=discarded.id.value))

    assert offered is not None
    assert withheld is None


async def test_get_reviewable_returns_none_for_an_id_no_note_holds(
    catalog_fixture: _Catalog,
) -> None:
    catalog, notes, cards = catalog_fixture
    note = _sample_note()
    await notes.save(note)
    await cards.save(_sample_card(note.id))

    stocked = await catalog.list_reviewable(_OWNER)
    result = await catalog.get_reviewable(_OWNER, CardId(value=uuid4()))

    assert len(stocked) == 1
    assert result is None
