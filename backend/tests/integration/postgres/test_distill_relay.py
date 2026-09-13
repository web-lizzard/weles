import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.in_memory.distill.structured_task import (
    DeterministicStructuredTaskAdapter,
)
from adapters.out.sqlalchemy.capture.unit_of_work import SqlAlchemyCaptureUnitOfWork
from adapters.out.sqlalchemy.distill.card_repository import SqlAlchemyCardRepository
from adapters.out.sqlalchemy.distill.note_repository import SqlAlchemyNoteRepository
from adapters.out.sqlalchemy.distill.unit_of_work import SqlAlchemyDistillUnitOfWork
from adapters.out.sqlalchemy.engine import create_engine, create_session_factory
from adapters.out.sqlalchemy.shared.outbox.claimer import SqlAlchemyOutboxClaimer
from adapters.out.worker.handlers.flashcard_gen import FlashcardGenHandler
from adapters.out.worker.handlers.note_save import SaveNoteHandler
from adapters.out.worker.outbox_worker import OutboxWorker
from application.capture.commands.approve_note import ApproveNoteCommand
from application.distill.commands.generate_cards import GenerateCardsCommand
from application.distill.commands.save_note import SaveNoteCommand
from domain.capture.capture_session import CaptureSession
from domain.capture.outbox import NOTE_APPROVED
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import Embedding, Label, NoteContent, SimilarityScore
from domain.capture.vocabulary import MatchCriteria
from domain.distill.card_factory import CardFactory
from domain.distill.outbox import NOTE_SAVED
from domain.distill.regeneration import RegenerationPolicy, ThresholdTier
from domain.distill.value_objects import (
    CardLengthPolicy,
    DiscardReason,
    DistillationStatus,
    NoteId,
)

pytestmark = pytest.mark.postgres

_EMBEDDING_MODEL = "test"
_MATCH = MatchCriteria(threshold=SimilarityScore(value=0.85))
_CARD_FRONT_MAX = 200
_CARD_BACK_MAX = 600
_OUTBOX_BATCH_SIZE = 10
_OUTBOX_MAX_ATTEMPTS = 3
_OUTBOX_WORKER_ID = "distill-relay-test"


def _never_regenerate_policy() -> RegenerationPolicy:
    return RegenerationPolicy(
        tiers=(ThresholdTier(max_length=None, min_accepted_share=0.0),)
    )


def _capture_uow(
    session_factory: async_sessionmaker[AsyncSession],
) -> SqlAlchemyCaptureUnitOfWork:
    return SqlAlchemyCaptureUnitOfWork(session_factory)


def _distill_uow_factory(
    session_factory: async_sessionmaker[AsyncSession],
) -> SqlAlchemyDistillUnitOfWork:
    return SqlAlchemyDistillUnitOfWork(session_factory)


def _relay_worker(
    session_factory: async_sessionmaker[AsyncSession],
) -> OutboxWorker:
    def uow_factory() -> SqlAlchemyDistillUnitOfWork:
        return _distill_uow_factory(session_factory)

    save_note_handler = SaveNoteHandler(
        SaveNoteCommand(uow_factory)  # pyright: ignore[reportArgumentType]
    )
    flashcard_gen_handler = FlashcardGenHandler(
        GenerateCardsCommand(
            uow_factory=uow_factory,  # pyright: ignore[reportArgumentType]
            structured_task=DeterministicStructuredTaskAdapter(),
            card_factory=CardFactory(
                CardLengthPolicy(front_max=_CARD_FRONT_MAX, back_max=_CARD_BACK_MAX)
            ),
            regeneration_policy=_never_regenerate_policy(),
        )
    )
    return OutboxWorker(
        SqlAlchemyOutboxClaimer(session_factory),
        [save_note_handler, flashcard_gen_handler],
        worker_id=_OUTBOX_WORKER_ID,
        batch_size=_OUTBOX_BATCH_SIZE,
        max_attempts=_OUTBOX_MAX_ATTEMPTS,
    )


def _sample_topic() -> Topic:
    return Topic.mint(
        Label(value="TCP handshakes"),
        Embedding(model=_EMBEDDING_MODEL, values=(0.1, 0.2)),
    )


def _sample_tag() -> Tag:
    return Tag.mint(
        Label(value="networking"),
        Embedding(model=_EMBEDDING_MODEL, values=(0.3, 0.4)),
    )


async def _load_distill_note(
    session_factory: async_sessionmaker[AsyncSession], note_id: NoteId
):
    async with session_factory() as db_session:
        return await SqlAlchemyNoteRepository(db_session).get(note_id)


async def _load_distill_cards(
    session_factory: async_sessionmaker[AsyncSession], note_id: NoteId
):
    async with session_factory() as db_session:
        return await SqlAlchemyCardRepository(db_session).list_by_note(note_id)


async def test_approve_note_and_one_run_once_produces_ready_distill_note_with_cards(
    engine: AsyncEngine,
    migrated_database_url: str,
) -> None:
    session_factory = create_session_factory(engine)
    capture_uow = _capture_uow(session_factory)
    session = CaptureSession.start()
    topic = _sample_topic()
    tag = _sample_tag()
    note = session.draft_note(
        topic,
        NoteContent(
            value=(
                "We discussed handshakes. "
                "Connections are established via a three-way handshake."
            )
        ),
        [tag],
    )
    async with capture_uow:
        await capture_uow.capture_sessions.save(session)
        await capture_uow.topics.add(topic)
        await capture_uow.tags.add(tag)
        await capture_uow.notes.add(note)
        await capture_uow.commit()

    approval = await ApproveNoteCommand(capture_uow).handle(  # pyright: ignore[reportArgumentType]
        session.id
    )
    note_id = NoteId(value=approval.note_id)

    acked = await _relay_worker(session_factory).run_once()
    assert acked == 2

    await engine.dispose()
    fresh_engine = create_engine(migrated_database_url)
    try:
        factory = create_session_factory(fresh_engine)
        distill_note = await _load_distill_note(factory, note_id)
        assert distill_note is not None
        assert distill_note.distillation_status == DistillationStatus.READY
        assert distill_note.topic.id == topic.id.value
        assert distill_note.topic.label == topic.label.value
        assert len(distill_note.tags) == 1
        assert distill_note.tags[0].id == tag.id.value
        assert distill_note.tags[0].label == tag.label.value

        cards = await _load_distill_cards(factory, note_id)
        live = [card for card in cards if card.discard is None]
        discarded = [
            card
            for card in cards
            if card.discard is not None
            and card.discard.reason == DiscardReason.UNGROUNDED
        ]
        assert live
        assert discarded
    finally:
        await fresh_engine.dispose()


async def test_relay_run_once_leaves_no_claimable_note_approved_or_note_saved_envelopes(
    engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(engine)
    capture_uow = _capture_uow(session_factory)
    session = CaptureSession.start()
    topic = _sample_topic()
    tag = _sample_tag()
    note = session.draft_note(
        topic,
        NoteContent(
            value=(
                "We discussed handshakes. "
                "Connections are established via a three-way handshake."
            )
        ),
        [tag],
    )
    async with capture_uow:
        await capture_uow.capture_sessions.save(session)
        await capture_uow.topics.add(topic)
        await capture_uow.tags.add(tag)
        await capture_uow.notes.add(note)
        await capture_uow.commit()

    _ = await ApproveNoteCommand(capture_uow).handle(  # pyright: ignore[reportArgumentType]
        session.id
    )

    worker = _relay_worker(session_factory)
    acked = await worker.run_once()
    assert acked == 2

    claimer = SqlAlchemyOutboxClaimer(session_factory)
    assert await claimer.claim(NOTE_APPROVED, limit=10, worker_id="w2") == []
    assert await claimer.claim(NOTE_SAVED, limit=10, worker_id="w2") == []
