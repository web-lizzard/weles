from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from adapters.out.sqlalchemy.distill.card_repository import SqlAlchemyCardRepository
from adapters.out.sqlalchemy.distill.note_repository import SqlAlchemyNoteRepository
from adapters.out.sqlalchemy.engine import create_session_factory
from domain.distill.card import Card
from domain.distill.note import Note
from domain.distill.ports import CardRepository, NoteRepository
from domain.distill.value_objects import (
    Anchor,
    CardId,
    CardSide,
    Discard,
    DiscardReason,
    DistillationStatus,
    NoteContent,
    NoteId,
    SessionId,
    TagSnapshot,
    TopicSnapshot,
)


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

    async def get(self, card_id: CardId) -> Card | None:
        async with self._session_factory() as db_session:
            return await SqlAlchemyCardRepository(db_session).get(card_id)

    async def list_by_note(self, note_id: NoteId) -> list[Card]:
        async with self._session_factory() as db_session:
            return await SqlAlchemyCardRepository(db_session).list_by_note(note_id)


@dataclass
class _CardFixture:
    cards: CardRepository
    notes: NoteRepository


def _sample_note(note_id: NoteId | None = None) -> Note:
    stamped_at = datetime.now(UTC)
    return Note(
        id=note_id or NoteId(value=uuid4()),
        session_id=SessionId(value=uuid4()),
        topic=TopicSnapshot(id=uuid4(), label="TCP handshakes"),
        content=NoteContent(value="Connections use a three-way handshake."),
        tags=[TagSnapshot(id=uuid4(), label="networking")],
        distillation_status=DistillationStatus.GENERATING,
        approved_at=stamped_at,
        created_at=stamped_at,
        updated_at=stamped_at,
    )


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


@pytest.fixture(
    params=["in_memory", pytest.param("postgres", marks=pytest.mark.postgres)]
)
def card_fixture(request: pytest.FixtureRequest) -> _CardFixture:
    if request.param == "in_memory":  # pyright: ignore[reportAny]
        return _CardFixture(
            cards=InMemoryCardRepository(),
            notes=InMemoryNoteRepository(),
        )
    engine: AsyncEngine = request.getfixturevalue("engine")  # pyright: ignore[reportAny]
    session_factory = create_session_factory(engine)
    return _CardFixture(
        cards=_CommittingCardRepository(session_factory),
        notes=_CommittingNoteRepository(session_factory),
    )


async def _seed_note(notes: NoteRepository, note_id: NoteId | None = None) -> Note:
    note = _sample_note(note_id)
    await notes.save(note)
    return note


async def test_get_returns_none_for_an_unknown_card_id(
    card_fixture: _CardFixture,
) -> None:
    result = await card_fixture.cards.get(CardId(value=uuid4()))

    assert result is None


async def test_get_returns_a_saved_card(card_fixture: _CardFixture) -> None:
    note = await _seed_note(card_fixture.notes)
    card = _sample_card(note.id)

    await card_fixture.cards.save(card)
    result = await card_fixture.cards.get(card.id)

    assert result == card


async def test_save_then_list_by_note_returns_the_saved_card(
    card_fixture: _CardFixture,
) -> None:
    note = await _seed_note(card_fixture.notes)
    card = _sample_card(note.id)

    await card_fixture.cards.save(card)
    result = await card_fixture.cards.list_by_note(note.id)

    assert result == [card]


async def test_list_by_note_returns_empty_for_a_note_with_no_cards(
    card_fixture: _CardFixture,
) -> None:
    note = await _seed_note(card_fixture.notes)
    await card_fixture.cards.save(_sample_card(note.id))

    result = await card_fixture.cards.list_by_note(NoteId(value=uuid4()))

    assert result == []


async def test_list_by_note_includes_discarded_cards(
    card_fixture: _CardFixture,
) -> None:
    note = await _seed_note(card_fixture.notes)
    live = _sample_card(note.id)
    discarded = _sample_card(
        note.id,
        discard=Discard(
            reason=DiscardReason.UNGROUNDED,
            detail=None,
            discarded_at=datetime.now(UTC),
        ),
    )

    await card_fixture.cards.save(live)
    await card_fixture.cards.save(discarded)
    result = await card_fixture.cards.list_by_note(note.id)

    assert result == [live, discarded] or result == [discarded, live]


async def test_second_save_with_same_id_overwrites(
    card_fixture: _CardFixture,
) -> None:
    note = await _seed_note(card_fixture.notes)
    original = _sample_card(note.id)
    updated = original.model_copy(
        update={
            "discard": Discard(
                reason=DiscardReason.OVERSIZED,
                detail="front exceeds front_max=10",
                discarded_at=datetime.now(UTC),
            )
        }
    )

    await card_fixture.cards.save(original)
    await card_fixture.cards.save(updated)
    result = await card_fixture.cards.list_by_note(note.id)

    assert result == [updated]


async def test_second_save_adds_discard_with_none_detail_reads_back_equal(
    card_fixture: _CardFixture,
) -> None:
    note = await _seed_note(card_fixture.notes)
    original = _sample_card(note.id)
    discarded_at = datetime.now(UTC)
    updated = original.model_copy(
        update={
            "discard": Discard(
                reason=DiscardReason.UNGROUNDED,
                detail=None,
                discarded_at=discarded_at,
            )
        }
    )

    await card_fixture.cards.save(original)
    await card_fixture.cards.save(updated)
    result = await card_fixture.cards.get(original.id)

    assert result == updated
