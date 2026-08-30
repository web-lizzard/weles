from adapters.out.in_memory.capture.message_store import InMemoryMessageStore
from application.capture.value_objects import Transcript
from domain.capture.value_objects import SessionId


class InMemoryTranscriptQueryAdapter:
    _store: InMemoryMessageStore

    def __init__(self, store: InMemoryMessageStore) -> None:
        self._store = store

    async def get_transcript(
        self,
        session_id: SessionId,  # pyright: ignore[reportUnusedParameter]
    ) -> Transcript:
        raise NotImplementedError
