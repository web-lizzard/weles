from datetime import UTC, datetime

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
from domain.capture.note import Note
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import (
    Embedding,
    Label,
    NoteContent,
    NoteId,
    NoteStatus,
    SessionId,
    TagId,
    TopicId,
)
from domain.shared.outbox.model import EnvelopeStatus, EnvelopeType, OutboxEnvelope

_EMBEDDING_MODEL = "test"


def _make_unit_of_work() -> tuple[
    InMemoryUnitOfWork,
    InMemoryNoteRepository,
    InMemoryTopicRepository,
    InMemoryTagRepository,
    InMemoryOutboxStore,
]:
    store = InMemoryMessageStore()
    session_repo = InMemoryCaptureSessionRepository()
    message_repo = InMemoryMessageRepository(store)
    note_repo = InMemoryNoteRepository()
    topic_repo = InMemoryTopicRepository()
    tag_repo = InMemoryTagRepository()
    outbox_store = InMemoryOutboxStore()
    outbox = InMemoryOutboxAppender(outbox_store)
    note_vocabulary = InMemoryNoteVocabularyRepository(topic_repo, tag_repo)
    uow = InMemoryUnitOfWork(
        session_repo,
        message_repo,
        store,
        note_repo,
        topic_repo,
        tag_repo,
        note_vocabulary,
        outbox_store,
        outbox,
    )
    return uow, note_repo, topic_repo, tag_repo, outbox_store


def _sample_topic() -> Topic:
    return Topic(
        id=TopicId.new(),
        label=Label(value="TCP handshakes"),
        embedding=Embedding(model=_EMBEDDING_MODEL, values=(0.1, 0.2)),
        created_at=datetime.now(UTC),
    )


def _sample_tag() -> Tag:
    return Tag(
        id=TagId.new(),
        label=Label(value="networking"),
        embedding=Embedding(model=_EMBEDDING_MODEL, values=(0.3, 0.4)),
        created_at=datetime.now(UTC),
    )


def _sample_note(topic: Topic, tag: Tag) -> Note:
    return Note(
        id=NoteId.new(),
        session_id=SessionId.new(),
        topic_id=topic.id,
        content=NoteContent(value="We discussed how connections are established."),
        tag_ids=[tag.id],
        status=NoteStatus.DRAFT,
        created_at=datetime.now(UTC),
        approved_at=None,
    )


async def test_rollback_without_commit_discards_notes_topics_and_tags() -> None:
    uow, note_repo, topic_repo, tag_repo, _ = _make_unit_of_work()
    note = _sample_note(_sample_topic(), _sample_tag())
    topic = _sample_topic()
    tag = _sample_tag()

    async with uow:
        await note_repo.add(note)
        await topic_repo.add(topic)
        await tag_repo.add(tag)

    assert await note_repo.get(note.id) is None
    assert await topic_repo.get(topic.id) is None
    assert await tag_repo.get(tag.id) is None


async def test_commit_persists_notes_topics_and_tags() -> None:
    uow, note_repo, topic_repo, tag_repo, _ = _make_unit_of_work()
    topic = _sample_topic()
    tag = _sample_tag()
    note = _sample_note(topic, tag)

    async with uow:
        await note_repo.add(note)
        await topic_repo.add(topic)
        await tag_repo.add(tag)
        await uow.commit()

    assert await note_repo.get(note.id) == note
    assert await topic_repo.get(topic.id) == topic
    assert await tag_repo.get(tag.id) == tag


async def test_rollback_without_commit_excludes_topics_and_tags_from_candidates() -> (
    None
):
    uow, _, topic_repo, tag_repo, _ = _make_unit_of_work()
    topic = _sample_topic()
    tag = _sample_tag()

    async with uow:
        await topic_repo.add(topic)
        await tag_repo.add(tag)

    assert await topic_repo.candidates() == []
    assert await tag_repo.candidates() == []


async def test_outbox_snapshot_restore_isolates_envelope_mutations_R2_F2() -> None:
    outbox_store = InMemoryOutboxStore()
    envelope = OutboxEnvelope.pending(
        EnvelopeType(name="note_approved"),
        {"note_id": "abc"},
    )
    await outbox_store.put(envelope)

    snapshot = outbox_store.snapshot()
    envelope.status = EnvelopeStatus.CONSUMED
    outbox_store.restore(snapshot)

    restored = outbox_store.all()[0]
    assert restored.status == EnvelopeStatus.PENDING
    assert restored is not envelope


async def test_rollback_without_commit_discards_outbox_envelopes() -> None:
    uow, _, _, _, outbox_store = _make_unit_of_work()
    envelope = OutboxEnvelope.pending(
        EnvelopeType(name="note_approved"),
        {"note_id": "abc"},
    )

    async with uow:
        await uow.outbox.append(envelope)

    assert outbox_store.all() == []
