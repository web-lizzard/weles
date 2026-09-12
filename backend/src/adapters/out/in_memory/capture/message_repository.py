from adapters.out.in_memory.capture.message_store import InMemoryMessageStore
from domain.capture.message import Message
from domain.capture.value_objects import SessionId


class InMemoryMessageRepository:
    _store: InMemoryMessageStore

    def __init__(self, store: InMemoryMessageStore) -> None:
        self._store = store

    async def add(self, message: Message) -> None:
        self._store.add(message)

    async def history(self, session_id: SessionId) -> list[Message]:
        return self._store.list_by_session(session_id)
