from typing import Protocol

from domain.distill.ports import NoteRepository
from domain.shared.outbox.ports import OutboxAppender


class UnitOfWork(Protocol):
    notes: NoteRepository
    outbox: OutboxAppender

    async def __aenter__(self) -> "UnitOfWork": ...

    async def __aexit__(self, *exc: object) -> None: ...

    async def commit(self) -> None: ...
