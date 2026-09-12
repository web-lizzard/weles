from collections.abc import AsyncIterator, Sequence
from contextlib import AbstractAsyncContextManager
from typing import Protocol

from domain.capture.capture_session import CaptureSession
from domain.capture.message import Message
from domain.capture.note import Note
from domain.capture.note_vocabulary import NoteVocabulary
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.turn import AgentEvent, CaptureTurn
from domain.capture.value_objects import Embedding, NoteId, SessionId, TagId, TopicId
from domain.shared.graph.model import Tool, ToolResult


class EmbeddingPort(Protocol):
    async def embed(self, text: str) -> Embedding: ...


class CaptureAgentPort(Protocol):
    """One turn of conversation with a model, expressed entirely in capture's
    own vocabulary.

    It is a domain port, not an application one, and it earns that by owing
    nothing to any transport: it takes the turn and the tools the current phase
    offers, and enters a conversation that yields `AgentEvent`s. Exiting the
    context closes the provider run. No chunk type, no provider type, no
    streaming protocol crosses it — `AbstractAsyncContextManager` and
    `AsyncIterator` are the only borrowed concepts and they are stdlib.
    Replacing the adapter library changes nothing here, which is FR-09.

    The tools arrive already filtered by the phase, and the adapter invokes
    their handlers with the same `turn` it was given. A tool reads and computes
    and never mutates, so nothing about state escapes into the adapter.

    This port is held by the application command, never by the state machine —
    `frame.md` is explicit that the machine is handed no model-facing port and
    consumes no stream, and that stays true: declaring the port beside the
    domain does not hand it to the machine.
    """

    def converse(
        self,
        turn: CaptureTurn,
        tools: Sequence[Tool[CaptureTurn, ToolResult]],
    ) -> AbstractAsyncContextManager[AsyncIterator[AgentEvent]]: ...


class CaptureSessionRepository(Protocol):
    async def get(self, session_id: SessionId) -> CaptureSession | None: ...

    async def save(self, session: CaptureSession) -> None: ...


class MessageRepository(Protocol):
    async def add(self, message: Message) -> None: ...

    async def history(self, session_id: SessionId) -> list[Message]: ...


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
