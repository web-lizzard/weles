from dataclasses import dataclass
from typing import cast

from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.distill.structured_task import (
    DeterministicStructuredTaskAdapter,
)
from adapters.out.in_memory.distill.unit_of_work import InMemoryUnitOfWork
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.claimer import InMemoryOutboxClaimer
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from adapters.out.worker.handlers.flashcard_gen import FlashcardGenHandler
from adapters.out.worker.handlers.note_save import SaveNoteHandler
from adapters.out.worker.outbox_worker import OutboxWorker
from application.distill.commands.generate_cards import GenerateCardsCommand
from application.distill.commands.save_note import SaveNoteCommand
from application.distill.ports import UnitOfWork as DistillUnitOfWork
from domain.distill.card_factory import CardFactory
from domain.distill.regeneration import RegenerationPolicy, ThresholdTier
from domain.distill.value_objects import CardLengthPolicy

_CARD_FRONT_MAX = 200
_CARD_BACK_MAX = 600
_OUTBOX_BATCH_SIZE = 10
_OUTBOX_MAX_ATTEMPTS = 3
_OUTBOX_WORKER_ID = "distill-test-worker"


def _never_regenerate_policy() -> RegenerationPolicy:
    return RegenerationPolicy(
        tiers=(ThresholdTier(max_length=None, min_accepted_share=0.0),)
    )


@dataclass
class InMemoryDistillComposition:
    notes: InMemoryNoteRepository
    cards: InMemoryCardRepository
    outbox_store: InMemoryOutboxStore
    outbox: InMemoryOutboxAppender
    structured_task: DeterministicStructuredTaskAdapter
    card_factory: CardFactory
    regeneration_policy: RegenerationPolicy

    @classmethod
    def create(cls, outbox_store: InMemoryOutboxStore) -> "InMemoryDistillComposition":
        return cls(
            notes=InMemoryNoteRepository(),
            cards=InMemoryCardRepository(),
            outbox_store=outbox_store,
            outbox=InMemoryOutboxAppender(outbox_store),
            structured_task=DeterministicStructuredTaskAdapter(),
            card_factory=CardFactory(
                CardLengthPolicy(front_max=_CARD_FRONT_MAX, back_max=_CARD_BACK_MAX)
            ),
            regeneration_policy=_never_regenerate_policy(),
        )

    def unit_of_work(self) -> DistillUnitOfWork:
        return cast(
            DistillUnitOfWork,
            cast(
                object,
                InMemoryUnitOfWork(
                    self.notes, self.cards, self.outbox_store, self.outbox
                ),
            ),
        )

    def worker(self) -> OutboxWorker:
        save_note_handler = SaveNoteHandler(
            SaveNoteCommand(uow_factory=self.unit_of_work)
        )
        flashcard_gen_handler = FlashcardGenHandler(
            GenerateCardsCommand(
                uow_factory=self.unit_of_work,
                structured_task=self.structured_task,
                card_factory=self.card_factory,
                regeneration_policy=self.regeneration_policy,
            )
        )
        claimer = InMemoryOutboxClaimer(self.outbox_store)
        return OutboxWorker(
            claimer,
            [save_note_handler, flashcard_gen_handler],
            worker_id=_OUTBOX_WORKER_ID,
            batch_size=_OUTBOX_BATCH_SIZE,
            max_attempts=_OUTBOX_MAX_ATTEMPTS,
        )
