from typing import Protocol

from application.distill.value_objects import CardProposal
from domain.distill.ports import CardRepository, NoteRepository
from domain.distill.value_objects import NoteContent
from domain.shared.outbox.ports import OutboxAppender


class CardGeneration(Protocol):
    async def generate(self, content: NoteContent) -> list[CardProposal]: ...


class NoteDocumentParser(Protocol):
    async def resolves(self, content: NoteContent, quote: str) -> bool: ...


class UnitOfWork(Protocol):
    notes: NoteRepository
    cards: CardRepository
    outbox: OutboxAppender

    async def __aenter__(self) -> "UnitOfWork": ...

    async def __aexit__(self, *exc: object) -> None: ...

    async def commit(self) -> None: ...
