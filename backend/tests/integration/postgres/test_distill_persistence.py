from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.sqlalchemy.distill.card_repository import SqlAlchemyCardRepository
from adapters.out.sqlalchemy.distill.note_repository import SqlAlchemyNoteRepository
from adapters.out.sqlalchemy.distill.unit_of_work import SqlAlchemyDistillUnitOfWork
from adapters.out.sqlalchemy.engine import create_engine, create_session_factory
from adapters.out.sqlalchemy.shared.outbox.claimer import SqlAlchemyOutboxClaimer
from application.distill.commands.discard_card import DiscardCardCommand
from application.distill.commands.save_note import SaveNoteCommand
from domain.distill.card import Card
from domain.distill.note import mint_note
from domain.distill.outbox import NOTE_SAVED, NoteSavedPayload
from domain.distill.value_objects import (
    Anchor,
    CardId,
    CardSide,
    DiscardReason,
    NoteContent,
    NoteId,
    SessionId,
    TagSnapshot,
    TopicSnapshot,
)
from domain.shared.identity.model import UserId

pytestmark = pytest.mark.postgres


def _distill_uow_factory(
    session_factory: async_sessionmaker[AsyncSession],
) -> SqlAlchemyDistillUnitOfWork:
    return SqlAlchemyDistillUnitOfWork(session_factory)


async def _load_note(
    session_factory: async_sessionmaker[AsyncSession], note_id: NoteId
):
    async with session_factory() as db_session:
        return await SqlAlchemyNoteRepository(db_session).get(note_id)


async def _load_card(
    session_factory: async_sessionmaker[AsyncSession], card_id: CardId
):
    async with session_factory() as db_session:
        return await SqlAlchemyCardRepository(db_session).get(card_id)


def _sample_live_card(note_id: NoteId) -> Card:
    return Card(
        id=CardId(value=uuid4()),
        owner_id=UserId.new(),
        note_id=note_id,
        front=CardSide(value="What establishes a connection?"),
        back=CardSide(value="A three-way handshake."),
        anchor=Anchor(quote="Connections are established via a three-way handshake."),
        discard=None,
        created_at=datetime.now(UTC),
    )


async def test_save_note_commits_note_and_claimable_note_saved_envelope(
    engine: AsyncEngine,
    migrated_database_url: str,
) -> None:
    session_factory = create_session_factory(engine)
    note_id = NoteId(value=uuid4())
    approved_at = datetime.now(UTC)
    topic = TopicSnapshot(id=uuid4(), label="TCP handshakes")
    tags = [TagSnapshot(id=uuid4(), label="networking")]

    await SaveNoteCommand(
        lambda: _distill_uow_factory(session_factory)  # pyright: ignore[reportArgumentType]
    ).handle(
        UserId.new(),
        note_id,
        SessionId(value=uuid4()),
        topic,
        NoteContent(value="We discussed handshakes."),
        tags,
        approved_at,
    )

    await engine.dispose()
    fresh_engine = create_engine(migrated_database_url)
    try:
        factory = create_session_factory(fresh_engine)
        persisted = await _load_note(factory, note_id)
        claimed = await SqlAlchemyOutboxClaimer(factory).claim(
            NOTE_SAVED, limit=10, worker_id="w1"
        )
        assert persisted is not None
        assert persisted.topic == topic
        assert persisted.tags == tags
        assert len(claimed) == 1
        assert claimed[0].payload["note_id"] == str(note_id.value)
    finally:
        await fresh_engine.dispose()


async def test_exception_after_note_save_and_outbox_append_leaves_neither_persisted(
    engine: AsyncEngine,
    migrated_database_url: str,
) -> None:
    session_factory = create_session_factory(engine)
    note_id = NoteId(value=uuid4())
    stamped_at = datetime.now(UTC)
    envelope = NoteSavedPayload(note_id=note_id.value).to_envelope()

    with pytest.raises(RuntimeError, match="boom"):
        async with _distill_uow_factory(session_factory) as uow:
            note = mint_note(
                UserId.new(),
                note_id,
                SessionId(value=uuid4()),
                TopicSnapshot(id=uuid4(), label="TCP handshakes"),
                NoteContent(value="We discussed handshakes."),
                [TagSnapshot(id=uuid4(), label="networking")],
                stamped_at,
            )
            await uow.notes.save(note)
            await uow.outbox.append(envelope)
            raise RuntimeError("boom")

    await engine.dispose()
    fresh_engine = create_engine(migrated_database_url)
    try:
        factory = create_session_factory(fresh_engine)
        claimed = await SqlAlchemyOutboxClaimer(factory).claim(
            NOTE_SAVED, limit=10, worker_id="w1"
        )
        assert await _load_note(factory, note_id) is None
        assert claimed == []
    finally:
        await fresh_engine.dispose()


async def test_discard_from_discard_card_command_survives_a_fresh_engine(
    engine: AsyncEngine,
    migrated_database_url: str,
) -> None:
    session_factory = create_session_factory(engine)
    note_id = NoteId(value=uuid4())
    card = _sample_live_card(note_id)
    stamped_at = datetime(2026, 5, 1, 14, 30, tzinfo=UTC)

    async with _distill_uow_factory(session_factory) as uow:
        note = mint_note(
            UserId.new(),
            note_id,
            SessionId(value=uuid4()),
            TopicSnapshot(id=uuid4(), label="TCP handshakes"),
            NoteContent(value="We discussed handshakes."),
            [],
            stamped_at,
        )
        await uow.notes.save(note)
        await uow.cards.save(card)
        await uow.commit()

    await DiscardCardCommand(
        lambda: _distill_uow_factory(session_factory)  # pyright: ignore[reportArgumentType]
    ).handle(card.id, DiscardReason.USER_AUDIT, "rejected during review", stamped_at)

    await engine.dispose()
    fresh_engine = create_engine(migrated_database_url)
    try:
        factory = create_session_factory(fresh_engine)
        persisted = await _load_card(factory, card.id)
        assert persisted is not None
        assert persisted.discard is not None
        assert persisted.discard.reason == DiscardReason.USER_AUDIT
        assert persisted.discard.detail == "rejected during review"
        assert persisted.discard.discarded_at == stamped_at
    finally:
        await fresh_engine.dispose()
