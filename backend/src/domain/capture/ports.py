from typing import Protocol

from domain.capture.capture_session import CaptureSession
from domain.capture.message import Message
from domain.capture.note import Note
from domain.capture.note_vocabulary import NoteVocabulary
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import NoteId, SessionId, TagId, TopicId


class CaptureSessionRepository(Protocol):
    async def get(self, session_id: SessionId) -> CaptureSession | None: ...

    async def save(self, session: CaptureSession) -> None: ...


class MessageRepository(Protocol):
    async def add(self, message: Message) -> None: ...


class NoteRepository(Protocol):
    async def add(self, note: Note) -> None: ...

    async def get(self, note_id: NoteId) -> Note | None: ...


class TopicRepository(Protocol):
    async def add(self, topic: Topic) -> None: ...

    async def get(self, topic_id: TopicId) -> Topic | None: ...

    async def candidates(self) -> list[Topic]: ...


class TagRepository(Protocol):
    async def add(self, tag: Tag) -> None: ...

    async def get(self, tag_id: TagId) -> Tag | None: ...

    async def candidates(self) -> list[Tag]: ...


class NoteVocabularyRepository(Protocol):
    async def resolve(self, note: Note) -> NoteVocabulary: ...
