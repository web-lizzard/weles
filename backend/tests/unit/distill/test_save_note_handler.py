import logging
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.distill.unit_of_work import InMemoryUnitOfWork
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from adapters.out.worker.handlers.note_save import SaveNoteHandler
from application.distill.commands.save_note import SaveNoteCommand
from domain.capture.outbox import NOTE_APPROVED, NoteApprovedPayload, VocabularySnapshot
from domain.distill.outbox import NOTE_SAVED
from domain.distill.value_objects import (
    NoteContent,
    NoteId,
    SessionId,
    TagSnapshot,
    TopicSnapshot,
)
from domain.shared.outbox.model import OutboxEnvelope


async def test_valid_envelope_persists_note_and_enqueues_note_saved() -> None:
    stack = _make_handler_stack()
    payload = NoteApprovedPayload(
        note_id=uuid4(),
        owner_id=uuid4(),
        session_id=uuid4(),
        topic=VocabularySnapshot(id=uuid4(), label="TCP handshakes"),
        content="  We discussed handshakes.  ",
        tags=[VocabularySnapshot(id=uuid4(), label="networking")],
        approved_at=datetime.now(UTC),
    )

    await stack.handler.handle(payload.to_envelope())

    persisted = await stack.notes_repo.get(NoteId(value=payload.note_id))
    assert persisted is not None
    assert persisted.session_id == SessionId(value=payload.session_id)
    assert persisted.topic == TopicSnapshot(
        id=payload.topic.id, label=payload.topic.label
    )
    assert persisted.content == NoteContent(value=payload.content)
    assert persisted.tags == [
        TagSnapshot(id=tag.id, label=tag.label) for tag in payload.tags
    ]
    assert persisted.approved_at == payload.approved_at

    envelopes = stack.outbox_store.all()
    assert len(envelopes) == 1
    assert envelopes[0].type == NOTE_SAVED
    assert envelopes[0].payload["note_id"] == str(payload.note_id)


async def test_malformed_envelope_is_logged_and_not_dispatched(
    caplog: pytest.LogCaptureFixture,
) -> None:
    stack = _make_handler_stack()
    envelope = OutboxEnvelope.pending(NOTE_APPROVED, {"session_id": str(uuid4())})

    with caplog.at_level(logging.ERROR):
        await stack.handler.handle(envelope)

    assert stack.notes_repo.snapshot() == {}
    assert stack.outbox_store.all() == []
    assert any(record.levelno >= logging.ERROR for record in caplog.records)


class _HandlerStack:
    notes_repo: InMemoryNoteRepository
    outbox_store: InMemoryOutboxStore
    handler: SaveNoteHandler

    def __init__(
        self,
        notes_repo: InMemoryNoteRepository,
        outbox_store: InMemoryOutboxStore,
        handler: SaveNoteHandler,
    ) -> None:
        self.notes_repo = notes_repo
        self.outbox_store = outbox_store
        self.handler = handler


def _make_handler_stack() -> _HandlerStack:
    notes_repo = InMemoryNoteRepository()
    cards_repo = InMemoryCardRepository()
    outbox_store = InMemoryOutboxStore()
    outbox = InMemoryOutboxAppender(outbox_store)

    def uow_factory() -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(notes_repo, cards_repo, outbox_store, outbox)

    command = SaveNoteCommand(uow_factory)  # pyright: ignore[reportArgumentType]
    handler = SaveNoteHandler(command)
    return _HandlerStack(notes_repo, outbox_store, handler)
