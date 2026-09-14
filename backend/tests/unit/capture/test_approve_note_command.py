import pytest

from adapters.out.in_memory.capture.capture_session_repository import (
    InMemoryCaptureSessionRepository,
)
from adapters.out.in_memory.capture.message_repository import (
    InMemoryMessageRepository,
)
from adapters.out.in_memory.capture.message_store import InMemoryMessageStore
from adapters.out.in_memory.capture.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.capture.note_vocabulary_repository import (
    InMemoryNoteVocabularyRepository,
)
from adapters.out.in_memory.capture.tag_repository import InMemoryTagRepository
from adapters.out.in_memory.capture.topic_repository import InMemoryTopicRepository
from adapters.out.in_memory.capture.unit_of_work import InMemoryUnitOfWork
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from application.capture.commands.approve_note import ApproveNoteCommand
from domain.capture.capture_session import CaptureSession
from domain.capture.exceptions import (
    CaptureSessionNotFoundError,
    NoteNotFoundError,
)
from domain.capture.outbox import NOTE_APPROVED
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import (
    Embedding,
    Label,
    NoteContent,
    NoteStatus,
    SessionId,
    SessionStatus,
)
from domain.shared.identity.model import UserId

_EMBEDDING_MODEL = "test"


async def test_approve_note_approves_note_closes_session_and_appends_envelope() -> None:
    stack = _make_approve_stack()
    owner = UserId.new()
    session = CaptureSession.start(owner)
    topic = Topic.mint(
        owner,
        Label(value="TCP handshakes"),
        Embedding(model=_EMBEDDING_MODEL, values=(0.1, 0.2)),
    )
    tag = Tag.mint(
        owner,
        Label(value="networking"),
        Embedding(model=_EMBEDDING_MODEL, values=(0.3, 0.4)),
    )
    note = session.draft_note(
        topic, NoteContent(value="We discussed handshakes."), [tag]
    )
    await stack.topics_repo.add(topic)
    await stack.tags_repo.add(tag)
    await stack.notes_repo.add(note)
    await stack.session_repo.save(session)

    response = await stack.command.handle(owner, session.id)

    assert response.note_id == note.id.value
    assert response.topic == "TCP handshakes"
    assert response.tags == ["networking"]
    assert response.approved_at is not None

    persisted_note = await stack.notes_repo.get(note.id)
    assert persisted_note is not None
    assert persisted_note.status == NoteStatus.APPROVED

    persisted_session = await stack.session_repo.get(session.id)
    assert persisted_session is not None
    assert persisted_session.status == SessionStatus.CLOSED

    envelopes = stack.outbox_store.all()
    assert len(envelopes) == 1
    assert envelopes[0].type == NOTE_APPROVED
    assert envelopes[0].payload["note_id"] == str(note.id.value)


async def test_approve_note_raises_not_found_for_unknown_session() -> None:
    stack = _make_approve_stack()

    with pytest.raises(CaptureSessionNotFoundError):
        _ = await stack.command.handle(UserId.new(), SessionId.new())


async def test_approve_note_raises_not_found_for_other_owners_session() -> None:
    stack = _make_approve_stack()
    owner_a = UserId.new()
    owner_b = UserId.new()
    session = CaptureSession.start(owner_a)
    topic = Topic.mint(
        owner_a,
        Label(value="TCP handshakes"),
        Embedding(model=_EMBEDDING_MODEL, values=(0.1, 0.2)),
    )
    tag = Tag.mint(
        owner_a,
        Label(value="networking"),
        Embedding(model=_EMBEDDING_MODEL, values=(0.3, 0.4)),
    )
    note = session.draft_note(
        topic, NoteContent(value="We discussed handshakes."), [tag]
    )
    await stack.topics_repo.add(topic)
    await stack.tags_repo.add(tag)
    await stack.notes_repo.add(note)
    await stack.session_repo.save(session)

    with pytest.raises(CaptureSessionNotFoundError):
        _ = await stack.command.handle(owner_b, session.id)


async def test_approve_note_rollback_on_missing_note_leaves_zero_envelopes() -> None:
    stack = _make_approve_stack()
    owner = UserId.new()
    session = CaptureSession.start(owner)
    topic = Topic.mint(
        owner,
        Label(value="TCP handshakes"),
        Embedding(model=_EMBEDDING_MODEL, values=(0.1, 0.2)),
    )
    tag = Tag.mint(
        owner,
        Label(value="networking"),
        Embedding(model=_EMBEDDING_MODEL, values=(0.3, 0.4)),
    )
    _ = session.draft_note(topic, NoteContent(value="Draft body"), [tag])
    await stack.session_repo.save(session)

    with pytest.raises(NoteNotFoundError):
        _ = await stack.command.handle(owner, session.id)

    assert stack.outbox_store.all() == []
    persisted_session = await stack.session_repo.get(session.id)
    assert persisted_session is not None
    assert persisted_session.status == SessionStatus.OPEN


class _ApproveStack:
    session_repo: InMemoryCaptureSessionRepository
    notes_repo: InMemoryNoteRepository
    topics_repo: InMemoryTopicRepository
    tags_repo: InMemoryTagRepository
    outbox_store: InMemoryOutboxStore
    command: ApproveNoteCommand

    def __init__(
        self,
        session_repo: InMemoryCaptureSessionRepository,
        notes_repo: InMemoryNoteRepository,
        topics_repo: InMemoryTopicRepository,
        tags_repo: InMemoryTagRepository,
        outbox_store: InMemoryOutboxStore,
        command: ApproveNoteCommand,
    ) -> None:
        self.session_repo = session_repo
        self.notes_repo = notes_repo
        self.topics_repo = topics_repo
        self.tags_repo = tags_repo
        self.outbox_store = outbox_store
        self.command = command


def _make_approve_stack() -> _ApproveStack:
    session_repo = InMemoryCaptureSessionRepository()
    message_store = InMemoryMessageStore()
    message_repo = InMemoryMessageRepository(message_store)
    notes_repo = InMemoryNoteRepository()
    topics_repo = InMemoryTopicRepository()
    tags_repo = InMemoryTagRepository()
    outbox_store = InMemoryOutboxStore()
    outbox = InMemoryOutboxAppender(outbox_store)
    note_vocabulary = InMemoryNoteVocabularyRepository(topics_repo, tags_repo)
    uow = InMemoryUnitOfWork(
        session_repo,
        message_repo,
        message_store,
        notes_repo,
        topics_repo,
        tags_repo,
        note_vocabulary,
        outbox_store,
        outbox,
    )
    command = ApproveNoteCommand(uow)  # pyright: ignore[reportArgumentType]
    return _ApproveStack(
        session_repo, notes_repo, topics_repo, tags_repo, outbox_store, command
    )
