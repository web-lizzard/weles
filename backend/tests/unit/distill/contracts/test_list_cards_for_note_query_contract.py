from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.list_cards_for_note_query import (
    InMemoryListCardsForNoteQueryAdapter,
)
from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from adapters.out.sqlalchemy.distill.card_repository import SqlAlchemyCardRepository
from adapters.out.sqlalchemy.distill.list_cards_for_note_query import (
    SqlAlchemyListCardsForNoteQueryAdapter,
)
from adapters.out.sqlalchemy.distill.note_repository import SqlAlchemyNoteRepository
from adapters.out.sqlalchemy.engine import create_session_factory
from application.distill.queries.list_cards_for_note import ListCardsForNoteQueryPort
from domain.distill.card import Card
from domain.distill.exceptions import DistillNoteNotFoundError
from domain.distill.note import Note
from domain.distill.note_document import NoteDocument
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
from domain.shared.identity.model import UserId

_CALLER = UserId.new()


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
class _ListCardsFixture:
    query: ListCardsForNoteQueryPort
    notes: NoteRepository
    cards: CardRepository


def _note(
    status: DistillationStatus,
    at: datetime,
    content: str = "We discussed how connections are established.",
    *,
    owner_id: UserId | None = None,
) -> Note:
    return Note(
        id=NoteId(value=uuid4()),
        owner_id=owner_id or _CALLER,
        session_id=SessionId(value=uuid4()),
        topic=TopicSnapshot(id=uuid4(), label="TCP handshakes"),
        content=NoteContent(value=content),
        tags=[TagSnapshot(id=uuid4(), label="networking")],
        distillation_status=status,
        approved_at=at,
        created_at=at,
        updated_at=at,
    )


def _card(
    note_id: NoteId,
    created_at: datetime,
    *,
    owner_id: UserId | None = None,
    quote: str = "Connections are established via a three-way handshake.",
    discard: Discard | None = None,
) -> Card:
    return Card(
        id=CardId(value=uuid4()),
        owner_id=owner_id or _CALLER,
        note_id=note_id,
        front=CardSide(value="What establishes a connection?"),
        back=CardSide(value="A three-way handshake."),
        anchor=Anchor(quote=quote),
        discard=discard,
        created_at=created_at,
    )


@pytest.fixture(
    params=["in_memory", pytest.param("postgres", marks=pytest.mark.postgres)]
)
def list_cards_fixture(request: pytest.FixtureRequest) -> _ListCardsFixture:
    if request.param == "in_memory":  # pyright: ignore[reportAny]
        notes = InMemoryNoteRepository()
        cards = InMemoryCardRepository()
        query: ListCardsForNoteQueryPort = InMemoryListCardsForNoteQueryAdapter(
            notes, cards
        )
        return _ListCardsFixture(query, notes, cards)
    engine: AsyncEngine = request.getfixturevalue("engine")  # pyright: ignore[reportAny]
    session_factory = create_session_factory(engine)
    notes = _CommittingNoteRepository(session_factory)
    cards = _CommittingCardRepository(session_factory)
    return _ListCardsFixture(
        cast(
            ListCardsForNoteQueryPort,
            cast(object, SqlAlchemyListCardsForNoteQueryAdapter(session_factory)),
        ),
        notes,
        cards,
    )


async def test_list_cards_for_note_returns_live_cards_ordered_by_created_at(
    list_cards_fixture: _ListCardsFixture,
) -> None:
    now = datetime.now(UTC)
    note = _note(DistillationStatus.READY, now)
    await list_cards_fixture.notes.save(note)
    older = _card(note.id, now)
    newer = _card(note.id, now + timedelta(minutes=5))
    await list_cards_fixture.cards.save(newer)
    await list_cards_fixture.cards.save(older)

    result = await list_cards_fixture.query.list_cards_for_note(_CALLER, note.id)

    assert [item.card_id for item in result] == [
        older.id.value,
        newer.id.value,
    ]


async def test_list_cards_for_note_omits_discarded_cards(
    list_cards_fixture: _ListCardsFixture,
) -> None:
    now = datetime.now(UTC)
    note = _note(DistillationStatus.READY, now)
    await list_cards_fixture.notes.save(note)
    live = _card(note.id, now)
    await list_cards_fixture.cards.save(live)
    await list_cards_fixture.cards.save(
        _card(
            note.id,
            now,
            discard=Discard(
                reason=DiscardReason.UNGROUNDED, detail=None, discarded_at=now
            ),
        )
    )

    result = await list_cards_fixture.query.list_cards_for_note(_CALLER, note.id)

    assert len(result) == 1
    assert result[0].card_id == live.id.value


async def test_list_cards_for_note_raises_not_found_for_an_unknown_note_id(
    list_cards_fixture: _ListCardsFixture,
) -> None:
    with pytest.raises(DistillNoteNotFoundError):
        _ = await list_cards_fixture.query.list_cards_for_note(
            UserId.new(), NoteId(value=uuid4())
        )


async def test_list_cards_for_note_reports_exact_block_and_unresolved_anchor_locations(
    list_cards_fixture: _ListCardsFixture,
) -> None:
    now = datetime.now(UTC)
    content = "# TCP Handshake\n\nThe client sends SYN and waits."
    exact_quote = "The client sends SYN and waits."
    heading_quote = "TCP Handshake"
    missing_quote = "a fragment that is no longer in this note"
    note = _note(DistillationStatus.READY, now, content=content)
    await list_cards_fixture.notes.save(note)
    await list_cards_fixture.cards.save(_card(note.id, now, quote=exact_quote))
    await list_cards_fixture.cards.save(
        _card(note.id, now + timedelta(seconds=1), quote=heading_quote)
    )
    await list_cards_fixture.cards.save(
        _card(note.id, now + timedelta(seconds=2), quote=missing_quote)
    )

    detail = await list_cards_fixture.query.list_cards_for_note(_CALLER, note.id)
    document = NoteDocument.of(note.content)
    blocks = document.blocks
    by_quote = {item.anchor_quote: item for item in detail}

    exact_location = by_quote[exact_quote].anchor_location
    assert exact_location is not None
    exact_block = blocks[exact_location.block_index].text
    assert exact_location.precision == "exact"
    assert exact_block[exact_location.start : exact_location.end] == exact_quote

    block_location = by_quote[heading_quote].anchor_location
    assert block_location is not None
    heading_block = blocks[block_location.block_index].text
    assert block_location.precision == "block"
    assert block_location.start == 0
    assert block_location.end == len(heading_block)

    assert by_quote[missing_quote].anchor_location is None


async def test_list_cards_for_note_raises_not_found_when_note_belongs_to_another_owner(
    list_cards_fixture: _ListCardsFixture,
) -> None:
    note_owner = UserId.new()
    caller = UserId.new()
    now = datetime.now(UTC)
    note = _note(DistillationStatus.READY, now, owner_id=note_owner)
    await list_cards_fixture.notes.save(note)
    await list_cards_fixture.cards.save(_card(note.id, now, owner_id=note_owner))

    with pytest.raises(DistillNoteNotFoundError):
        _ = await list_cards_fixture.query.list_cards_for_note(caller, note.id)
