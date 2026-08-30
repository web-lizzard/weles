from domain.capture.message import Message
from domain.capture.value_objects import SessionId


class InMemoryMessageStore:
    def add(self, message: Message) -> None:  # pyright: ignore[reportUnusedParameter]
        raise NotImplementedError

    def list_by_session(
        self,
        session_id: SessionId,  # pyright: ignore[reportUnusedParameter]
    ) -> list[Message]:
        raise NotImplementedError
