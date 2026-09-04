from uuid import UUID

from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from domain.distill.card import Card
from domain.distill.note import Note
from domain.shared.outbox.model import OutboxEnvelope


class InMemoryUnitOfWork:
    notes: InMemoryNoteRepository
    cards: InMemoryCardRepository
    outbox: InMemoryOutboxAppender

    def __init__(
        self,
        notes: InMemoryNoteRepository,
        cards: InMemoryCardRepository,
        outbox_store: InMemoryOutboxStore,
        outbox: InMemoryOutboxAppender,
    ) -> None:
        self.notes = notes
        self.cards = cards
        self.outbox = outbox
        self._outbox_store: InMemoryOutboxStore = outbox_store
        self._committed: bool = False
        self._notes_snapshot: dict[UUID, Note] = {}
        self._cards_snapshot: dict[UUID, Card] = {}
        self._outbox_snapshot: dict[UUID, OutboxEnvelope] = {}

    async def __aenter__(self) -> "InMemoryUnitOfWork":
        self._committed = False
        self._notes_snapshot = self.notes.snapshot()
        self._cards_snapshot = self.cards.snapshot()
        self._outbox_snapshot = self._outbox_store.snapshot()
        return self

    async def __aexit__(self, *exc: object) -> None:
        if not self._committed:
            self.notes.restore(self._notes_snapshot)
            self.cards.restore(self._cards_snapshot)
            self._outbox_store.restore(self._outbox_snapshot)

    async def commit(self) -> None:
        self._committed = True
