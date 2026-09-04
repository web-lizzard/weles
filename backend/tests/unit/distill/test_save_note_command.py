import logging
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.distill.unit_of_work import InMemoryUnitOfWork
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from application.distill.commands.save_note import SaveNoteCommand
from domain.distill.outbox import NOTE_SAVED
from domain.distill.value_objects import (
    DistillationStatus,
    NoteContent,
    NoteId,
    SessionId,
    TagSnapshot,
    TopicSnapshot,
)


async def test_save_note_persists_generating_note_and_enqueues_note_saved() -> None:
    stack = _make_save_stack()
    note_id = NoteId(value=uuid4())

    await stack.command.handle(
        note_id,
        SessionId(value=uuid4()),
        TopicSnapshot(id=uuid4(), label="TCP handshakes"),
        NoteContent(value="We discussed handshakes."),
        [TagSnapshot(id=uuid4(), label="networking")],
        datetime.now(UTC),
    )

    persisted = await stack.notes_repo.get(note_id)
    assert persisted is not None
    assert persisted.distillation_status == DistillationStatus.GENERATING

    envelopes = stack.outbox_store.all()
    assert len(envelopes) == 1
    assert envelopes[0].type == NOTE_SAVED
    assert envelopes[0].payload["note_id"] == str(note_id.value)


async def test_save_note_redelivery_is_a_logged_no_op(
    caplog: pytest.LogCaptureFixture,
) -> None:
    stack = _make_save_stack()
    note_id = NoteId(value=uuid4())
    args = (
        note_id,
        SessionId(value=uuid4()),
        TopicSnapshot(id=uuid4(), label="TCP handshakes"),
        NoteContent(value="We discussed handshakes."),
        [TagSnapshot(id=uuid4(), label="networking")],
        datetime.now(UTC),
    )
    await stack.command.handle(*args)

    with caplog.at_level(logging.INFO):
        await stack.command.handle(*args)

    assert len(stack.notes_repo.snapshot()) == 1
    assert len(stack.outbox_store.all()) == 1
    assert any(
        "redeliver" in record.message.lower()
        or "no-op" in record.message.lower()
        or "no_op" in record.message.lower()
        for record in caplog.records
    )


class _SaveStack:
    notes_repo: InMemoryNoteRepository
    outbox_store: InMemoryOutboxStore
    command: SaveNoteCommand

    def __init__(
        self,
        notes_repo: InMemoryNoteRepository,
        outbox_store: InMemoryOutboxStore,
        command: SaveNoteCommand,
    ) -> None:
        self.notes_repo = notes_repo
        self.outbox_store = outbox_store
        self.command = command


def _make_save_stack() -> _SaveStack:
    notes_repo = InMemoryNoteRepository()
    outbox_store = InMemoryOutboxStore()
    outbox = InMemoryOutboxAppender(outbox_store)

    def uow_factory() -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(notes_repo, outbox_store, outbox)

    command = SaveNoteCommand(uow_factory)  # pyright: ignore[reportArgumentType]
    return _SaveStack(notes_repo, outbox_store, command)
