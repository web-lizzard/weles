from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.list_notes_query import (
    InMemoryListNotesQueryAdapter,
)
from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from adapters.out.sqlalchemy.distill.card_repository import SqlAlchemyCardRepository
from adapters.out.sqlalchemy.distill.list_notes_query import (
    SqlAlchemyListNotesQueryAdapter,
)
from adapters.out.sqlalchemy.distill.note_repository import SqlAlchemyNoteRepository
from adapters.out.sqlalchemy.engine import create_session_factory
from application.distill.queries.list_notes import ListNotesQueryPort
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
class _ListNotesFixture:
    query: ListNotesQueryPort
    notes: NoteRepository
    cards: CardRepository


def _note(
    status: DistillationStatus,
    updated_at: datetime,
    note_id: NoteId | None = None,
) -> Note:
    return Note(
        id=note_id or NoteId(value=uuid4()),
        session_id=SessionId(value=uuid4()),
        topic=TopicSnapshot(id=uuid4(), label="TCP handshakes"),
        content=NoteContent(value="We discussed how connections are established."),
        tags=[TagSnapshot(id=uuid4(), label="networking")],
        distillation_status=status,
        approved_at=updated_at,
        created_at=updated_at,
        updated_at=updated_at,
    )


def _card(
    note_id: NoteId, created_at: datetime, discard: Discard | None = None
) -> Card:
    return Card(
        id=CardId(value=uuid4()),
        note_id=note_id,
        front=CardSide(value="What establishes a connection?"),
        back=CardSide(value="A three-way handshake."),
        anchor=Anchor(quote="Connections are established via a three-way handshake."),
        discard=discard,
        created_at=created_at,
    )


@pytest.fixture(
    params=["in_memory", pytest.param("postgres", marks=pytest.mark.postgres)]
)
def list_notes_fixture(request: pytest.FixtureRequest) -> _ListNotesFixture:
    if request.param == "in_memory":  # pyright: ignore[reportAny]
        notes = InMemoryNoteRepository()
        cards = InMemoryCardRepository()
        query: ListNotesQueryPort = InMemoryListNotesQueryAdapter(notes, cards)
        return _ListNotesFixture(query, notes, cards)
    engine: AsyncEngine = request.getfixturevalue("engine")  # pyright: ignore[reportAny]
    session_factory = create_session_factory(engine)
    notes = _CommittingNoteRepository(session_factory)
    cards = _CommittingCardRepository(session_factory)
    query = SqlAlchemyListNotesQueryAdapter(session_factory)
    return _ListNotesFixture(query, notes, cards)


async def test_list_notes_returns_empty_list_when_no_notes_saved(
    list_notes_fixture: _ListNotesFixture,
) -> None:
    result = await list_notes_fixture.query.list_notes()

    assert result == []


async def test_list_notes_exposes_raw_distillation_status_per_note(
    list_notes_fixture: _ListNotesFixture,
) -> None:
    now = datetime.now(UTC)
    generating = _note(DistillationStatus.GENERATING, now)
    ready = _note(DistillationStatus.READY, now)
    failed = _note(DistillationStatus.FAILED, now)
    for note in (generating, ready, failed):
        await list_notes_fixture.notes.save(note)

    result = await list_notes_fixture.query.list_notes()

    statuses = {item.note_id: item.distillation_status for item in result}
    assert statuses[generating.id.value] == "generating"
    assert statuses[ready.id.value] == "ready"
    assert statuses[failed.id.value] == "failed"


async def test_list_notes_card_count_excludes_discarded_cards(
    list_notes_fixture: _ListNotesFixture,
) -> None:
    now = datetime.now(UTC)
    note = _note(DistillationStatus.READY, now)
    await list_notes_fixture.notes.save(note)
    await list_notes_fixture.cards.save(_card(note.id, now))
    await list_notes_fixture.cards.save(_card(note.id, now))
    await list_notes_fixture.cards.save(
        _card(
            note.id,
            now,
            discard=Discard(
                reason=DiscardReason.UNGROUNDED, detail=None, discarded_at=now
            ),
        )
    )

    result = await list_notes_fixture.query.list_notes()

    assert result[0].card_count == 2


async def test_list_notes_reports_zero_cards_and_note_updated_at_when_no_cards(
    list_notes_fixture: _ListNotesFixture,
) -> None:
    updated_at = datetime.now(UTC)
    note = _note(DistillationStatus.READY, updated_at)
    await list_notes_fixture.notes.save(note)

    result = await list_notes_fixture.query.list_notes()

    assert len(result) == 1
    assert result[0].card_count == 0
    assert result[0].last_updated_at == note.updated_at


async def test_list_notes_orders_by_recency_using_max_of_note_and_card_timestamps(
    list_notes_fixture: _ListNotesFixture,
) -> None:
    t1 = datetime.now(UTC)
    t3 = t1 + timedelta(minutes=3)
    t4 = t1 + timedelta(minutes=4)

    stale_by_own_timestamp_alone = _note(DistillationStatus.READY, t3)
    recent_only_because_of_its_card = _note(DistillationStatus.GENERATING, t1)
    await list_notes_fixture.notes.save(stale_by_own_timestamp_alone)
    await list_notes_fixture.notes.save(recent_only_because_of_its_card)
    await list_notes_fixture.cards.save(_card(recent_only_because_of_its_card.id, t4))

    result = await list_notes_fixture.query.list_notes()

    assert result[0].note_id == recent_only_because_of_its_card.id.value
    assert result[1].note_id == stale_by_own_timestamp_alone.id.value
