from collections.abc import Callable

import pytest

from adapters.out.in_memory.capture.message_store import InMemoryMessageStore
from adapters.out.in_memory.capture.transcript_query import (
    InMemoryTranscriptQueryAdapter,
)
from application.capture.queries.transcript import TranscriptQueryPort
from application.capture.value_objects import TranscriptEntry
from domain.capture.message import Message
from domain.capture.value_objects import MessageContent, MessageRole, SessionId


def _make_in_memory() -> tuple[TranscriptQueryPort, InMemoryMessageStore]:
    store = InMemoryMessageStore()
    return InMemoryTranscriptQueryAdapter(store), store


_IMPLEMENTATIONS: list[
    Callable[[], tuple[TranscriptQueryPort, InMemoryMessageStore]]
] = [
    _make_in_memory,
]


@pytest.mark.parametrize("make_adapter", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_get_transcript_maps_stored_messages_in_insertion_order(
    make_adapter: Callable[[], tuple[TranscriptQueryPort, InMemoryMessageStore]],
) -> None:
    adapter, store = make_adapter()
    session_id = SessionId.new()
    first = Message.record(
        session_id=session_id,
        role=MessageRole.USER,
        content=MessageContent(value="first turn"),
    )
    second = Message.record(
        session_id=session_id,
        role=MessageRole.AGENT,
        content=MessageContent(value="second turn"),
    )
    store.add(first)
    store.add(second)

    transcript = await adapter.get_transcript(session_id)

    assert transcript == [
        TranscriptEntry(role=first.role, content=first.content),
        TranscriptEntry(role=second.role, content=second.content),
    ]
