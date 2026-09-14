from datetime import UTC, datetime
from typing import NamedTuple
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.remember.card_source_locator import (
    InMemoryCardSourceLocator,
)
from adapters.out.sqlalchemy.distill.card_repository import SqlAlchemyCardRepository
from adapters.out.sqlalchemy.distill.note_repository import SqlAlchemyNoteRepository
from adapters.out.sqlalchemy.engine import create_session_factory
from adapters.out.sqlalchemy.remember.card_source_locator import (
    SqlAlchemyCardSourceLocator,
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


class _Locator(NamedTuple):
    """The port under test plus the seams a contract case seeds through."""

    locator: CardSourceLocator
    notes: NoteRepository
    cards: CardRepository


@pytest.fixture(
    params=["in_memory", pytest.param("postgres", marks=pytest.mark.postgres)]
)
def locator_fixture(
    request: pytest.FixtureRequest,
) -> tuple[_Locator, str]:
    implementation = str(request.param)  # pyright: ignore[reportAny]
    if implementation == "in_memory":
        notes = InMemoryNoteRepository()
        cards = InMemoryCardRepository()
        return _Locator(InMemoryCardSourceLocator(notes, cards), notes, cards), (
            implementation
        )
    engine: AsyncEngine = request.getfixturevalue("engine")  # pyright: ignore[reportAny]
    session_factory = create_session_factory(engine)
    notes = _CommittingNoteRepository(session_factory)
    cards = _CommittingCardRepository(session_factory)
    return _Locator(SqlAlchemyCardSourceLocator(session_factory), notes, cards), (
        implementation
    )


def _sample_note(content: str | None = None) -> Note:
    body = (
        content
        if content is not None
        else "Connections are established via a three-way handshake."
    )
    return mint_note(
        UserId.new(),
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
        owner_id=UserId.new(),
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


async def test_locate_returns_every_block_and_exact_span_when_anchor_matches(
    locator_fixture: tuple[_Locator, str],
) -> None:
    locator, notes, cards = locator_fixture[0]
    note_body = (
        "Lead paragraph.\n\n"
        "Connections are established via a three-way handshake.\n\n"
        "Tail."
    )
    note = _sample_note(note_body)
    card = _sample_card(note.id)
    await notes.save(note)
    await cards.save(card)

    result = await locator.locate(_OWNER, CardId(value=card.id.value))

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


async def test_locate_returns_none_for_a_card_id_no_repository_holds(
    locator_fixture: tuple[_Locator, str],
) -> None:
    locator, notes, cards = locator_fixture[0]
    note = _sample_note()
    card = _sample_card(note.id)
    await notes.save(note)
    await cards.save(card)

    result = await locator.locate(_OWNER, CardId(value=uuid4()))

    assert result is None


async def test_locate_returns_none_for_a_discarded_card(
    locator_fixture: tuple[_Locator, str],
) -> None:
    locator, notes, cards = locator_fixture[0]
    note = _sample_note()
    card = _sample_card(note.id, discard=_discarded())
    await notes.save(note)
    await cards.save(card)

    result = await locator.locate(_OWNER, CardId(value=card.id.value))

    assert result is None


async def test_locate_returns_none_when_the_note_behind_the_card_is_missing(
    locator_fixture: tuple[_Locator, str],
) -> None:
    fixture, implementation = locator_fixture
    if implementation == "postgres":
        pytest.skip(
            "distill_cards.note_id foreign key prevents orphan cards on Postgres"
        )
    locator, _notes, cards = fixture
    note = _sample_note()
    card = _sample_card(note.id)
    await cards.save(card)

    result = await locator.locate(_OWNER, CardId(value=card.id.value))

    assert result is None


async def test_locate_returns_none_when_the_note_no_longer_contains_the_card_quote(
    locator_fixture: tuple[_Locator, str],
) -> None:
    locator, notes, cards = locator_fixture[0]
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

    result = await locator.locate(_OWNER, CardId(value=card.id.value))

    assert result is None
