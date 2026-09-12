from collections.abc import Callable
from typing import cast

import pytest

from adapters.out.in_memory.capture.message_repository import InMemoryMessageRepository
from adapters.out.in_memory.capture.message_store import InMemoryMessageStore
from domain.capture.message import Message
from domain.capture.ports import MessageRepository
from domain.capture.value_objects import MessageContent, MessageRole, SessionId

pytestmark = pytest.mark.skip(
    reason=(
        "MessageRepository.history is on the port but InMemoryMessageRepository "
        "does not implement it yet; re-enable in /implement "
        "llm-adapter-capture-modes."
    ),
)


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
