from uuid import UUID

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
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from domain.capture.capture_session import CaptureSession
from domain.capture.message import Message
from domain.capture.note import Note
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.shared.outbox.model import OutboxEnvelope


class InMemoryUnitOfWork:
    capture_sessions: InMemoryCaptureSessionRepository
    messages: InMemoryMessageRepository
    notes: InMemoryNoteRepository
    topics: InMemoryTopicRepository
    tags: InMemoryTagRepository
    note_vocabulary: InMemoryNoteVocabularyRepository
    outbox: InMemoryOutboxAppender

    def __init__(
        self,
        capture_sessions: InMemoryCaptureSessionRepository,
        messages: InMemoryMessageRepository,
        message_store: InMemoryMessageStore,
        notes: InMemoryNoteRepository,
        topics: InMemoryTopicRepository,
        tags: InMemoryTagRepository,
        note_vocabulary: InMemoryNoteVocabularyRepository,
        outbox_store: InMemoryOutboxStore,
        outbox: InMemoryOutboxAppender,
    ) -> None:
        self.capture_sessions = capture_sessions
        self.messages = messages
        self.notes = notes
        self.topics = topics
        self.tags = tags
        self.note_vocabulary = note_vocabulary
        self.outbox = outbox
        self._message_store: InMemoryMessageStore = message_store
        self._outbox_store: InMemoryOutboxStore = outbox_store
        self._committed: bool = False
        self._sessions_snapshot: dict[UUID, CaptureSession] = {}
        self._messages_snapshot: dict[UUID, list[Message]] = {}
        self._notes_snapshot: dict[UUID, Note] = {}
        self._topics_snapshot: dict[UUID, Topic] = {}
        self._tags_snapshot: dict[UUID, Tag] = {}
        self._outbox_snapshot: dict[UUID, OutboxEnvelope] = {}

    async def __aenter__(self) -> "InMemoryUnitOfWork":
        self._committed = False
        self._sessions_snapshot = self.capture_sessions.snapshot()
        self._messages_snapshot = self._message_store.snapshot()
        self._notes_snapshot = self.notes.snapshot()
        self._topics_snapshot = self.topics.snapshot()
        self._tags_snapshot = self.tags.snapshot()
        self._outbox_snapshot = self._outbox_store.snapshot()
        return self

    async def __aexit__(self, *exc: object) -> None:
        if not self._committed:
            self.capture_sessions.restore(self._sessions_snapshot)
            self._message_store.restore(self._messages_snapshot)
            self.notes.restore(self._notes_snapshot)
            self.topics.restore(self._topics_snapshot)
            self.tags.restore(self._tags_snapshot)
            self._outbox_store.restore(self._outbox_snapshot)

    async def commit(self) -> None:
        self._committed = True
