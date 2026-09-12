from collections.abc import Callable
from typing import cast

import pytest

from adapters.out.in_memory.capture.message_repository import InMemoryMessageRepository
from adapters.out.in_memory.capture.message_store import InMemoryMessageStore
from domain.capture.message import Message
from domain.capture.ports import MessageRepository
from domain.capture.value_objects import MessageContent, MessageRole, SessionId


def _make_in_memory() -> tuple[MessageRepository, InMemoryMessageStore]:
    store = InMemoryMessageStore()
    repository = InMemoryMessageRepository(store)
    return cast(MessageRepository, cast(object, repository)), store


_IMPLEMENTATIONS: list[Callable[[], tuple[MessageRepository, InMemoryMessageStore]]] = [
    _make_in_memory,
]


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_add_persists_message_visible_via_the_shared_store(
    make_repository: Callable[[], tuple[MessageRepository, InMemoryMessageStore]],
) -> None:
    repository, store = make_repository()
    message = Message.record(
        session_id=SessionId.new(),
        role=MessageRole.USER,
        content=MessageContent(value="Let's talk about TCP handshakes"),
    )

    await repository.add(message)

    assert store.list_by_session(message.session_id) == [message]


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_history_returns_messages_for_session_in_order(
    make_repository: Callable[[], tuple[MessageRepository, InMemoryMessageStore]],
) -> None:
    repository, _store = make_repository()
    session_id = SessionId.new()
    first = Message.record(
        session_id=session_id,
        role=MessageRole.USER,
        content=MessageContent(value="First"),
    )
    second = Message.record(
        session_id=session_id,
        role=MessageRole.AGENT,
        content=MessageContent(value="Second"),
    )
    other_session = Message.record(
        session_id=SessionId.new(),
        role=MessageRole.USER,
        content=MessageContent(value="Other"),
    )

    await repository.add(first)
    await repository.add(second)
    await repository.add(other_session)

    history = await repository.history(session_id)

    assert history == [first, second]


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_history_returns_empty_list_when_session_has_no_messages(
    make_repository: Callable[[], tuple[MessageRepository, InMemoryMessageStore]],
) -> None:
    repository, _store = make_repository()

    assert await repository.history(SessionId.new()) == []
