import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import cast

from adapters.compose import (
    get_card_source_query,
    get_current_card_query,
    get_due_count_query,
    get_grade_card_command,
    get_open_sitting_command,
    get_reject_card_command,
    get_reveal_back_command,
)
from adapters.out.fsrs.scheduler import FsrsScheduler
from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.note_repository import (
    InMemoryNoteRepository as InMemoryDistillNoteRepository,
)
from adapters.out.in_memory.distill.unit_of_work import (
    InMemoryUnitOfWork as InMemoryDistillUnitOfWork,
)
from adapters.out.in_memory.remember.card_source_locator import (
    InMemoryCardSourceLocator,
)
from adapters.out.in_memory.remember.clock import SystemClock
from adapters.out.in_memory.remember.review_catalog import InMemoryReviewCatalog
from adapters.out.in_memory.remember.review_event_store import InMemoryReviewEventStore
from adapters.out.in_memory.remember.scheduling_state_repository import (
    InMemorySchedulingStateRepository,
)
from adapters.out.in_memory.remember.sitting_repository import InMemorySittingRepository
from adapters.out.in_memory.remember.unit_of_work import (
    InMemoryUnitOfWork,
)
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.claimer import InMemoryOutboxClaimer
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from adapters.out.worker.handlers.card_discard import CardDiscardHandler
from adapters.out.worker.outbox_worker import OutboxWorker
from application.distill.commands.discard_card import DiscardCardCommand
from application.distill.ports import UnitOfWork as DistillUnitOfWork
from application.remember.commands.grade_card import GradeCardCommand
from application.remember.commands.open_sitting import OpenSittingCommand
from application.remember.commands.reject_card import RejectCardCommand
from application.remember.commands.reveal_back import RevealBackCommand
from application.remember.ports import Clock, UnitOfWork
from application.remember.queries.card_source import CardSourceQuery
from application.remember.queries.current_card import CurrentCardQuery
from application.remember.queries.due_count import DueCountQuery
from domain.remember.value_objects import (
    MIN_RESUME_HORIZON,
    ResumeHorizon,
    ShowingLimit,
)

_DEFAULT_SHOWING_LIMIT = 2
_OUTBOX_BATCH_SIZE = 10
_OUTBOX_MAX_ATTEMPTS = 3
_OUTBOX_WORKER_ID = "remember-test-worker"


@dataclass
class InMemoryRememberComposition:
    sittings: InMemorySittingRepository
    review_events: InMemoryReviewEventStore
    scheduling_states: InMemorySchedulingStateRepository
    catalog: InMemoryReviewCatalog
    scheduler: FsrsScheduler
    clock: Clock
    showing_limit: ShowingLimit
    resume_horizon: ResumeHorizon
    notes: InMemoryDistillNoteRepository
    cards: InMemoryCardRepository
    outbox_store: InMemoryOutboxStore
    outbox: InMemoryOutboxAppender
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @classmethod
    def create(
        cls,
        clock: Clock | None = None,
        showing_limit: ShowingLimit | None = None,
        resume_horizon: ResumeHorizon | None = None,
    ) -> "InMemoryRememberComposition":
        notes = InMemoryDistillNoteRepository()
        cards = InMemoryCardRepository()
        outbox_store = InMemoryOutboxStore()
        return cls(
            sittings=InMemorySittingRepository(),
            review_events=InMemoryReviewEventStore(),
            scheduling_states=InMemorySchedulingStateRepository(),
            catalog=InMemoryReviewCatalog(notes, cards),
            scheduler=FsrsScheduler(),
            clock=clock or SystemClock(),
            showing_limit=showing_limit or ShowingLimit(value=_DEFAULT_SHOWING_LIMIT),
            resume_horizon=resume_horizon or ResumeHorizon(value=MIN_RESUME_HORIZON),
            notes=notes,
            cards=cards,
            outbox_store=outbox_store,
            outbox=InMemoryOutboxAppender(outbox_store),
        )

    def unit_of_work(self) -> UnitOfWork:
        return cast(
            UnitOfWork,
            cast(
                object,
                InMemoryUnitOfWork(
                    self.sittings,
                    self.review_events,
                    self.scheduling_states,
                    self.outbox_store,
                    self.outbox,
                    self.lock,
                ),
            ),
        )

    def distill_unit_of_work(self) -> DistillUnitOfWork:
        return cast(
            DistillUnitOfWork,
            cast(
                object,
                InMemoryDistillUnitOfWork(
                    self.notes, self.cards, self.outbox_store, self.outbox
                ),
            ),
        )

    def worker(self) -> OutboxWorker:
        card_discard_handler = CardDiscardHandler(
            DiscardCardCommand(uow_factory=self.distill_unit_of_work)
        )
        claimer = InMemoryOutboxClaimer(self.outbox_store)
        return OutboxWorker(
            claimer,
            [card_discard_handler],
            worker_id=_OUTBOX_WORKER_ID,
            batch_size=_OUTBOX_BATCH_SIZE,
            max_attempts=_OUTBOX_MAX_ATTEMPTS,
        )

    def open_sitting(self) -> OpenSittingCommand:
        return OpenSittingCommand(
            uow_factory=self.unit_of_work,
            catalog=self.catalog,
            clock=self.clock,
            showing_limit=self.showing_limit,
            scheduler=self.scheduler,
            resume_horizon=self.resume_horizon,
        )

    def grade_card(self) -> GradeCardCommand:
        return GradeCardCommand(
            uow_factory=self.unit_of_work,
            catalog=self.catalog,
            scheduler=self.scheduler,
            clock=self.clock,
        )

    def reject_card(self) -> RejectCardCommand:
        return RejectCardCommand(
            uow_factory=self.unit_of_work,
            catalog=self.catalog,
            clock=self.clock,
        )

    def current_card(self) -> CurrentCardQuery:
        return CurrentCardQuery(
            self.sittings,
            self.review_events,
            self.catalog,
            self.scheduling_states,
            self.clock,
            self.scheduler,
        )

    def due_count(self) -> DueCountQuery:
        return DueCountQuery(
            self.sittings,
            self.review_events,
            self.catalog,
            self.scheduling_states,
            self.clock,
            self.scheduler,
        )

    def reveal_back(self) -> RevealBackCommand:
        return RevealBackCommand(
            uow_factory=self.unit_of_work,
            catalog=self.catalog,
            clock=self.clock,
        )

    def card_source(self) -> CardSourceQuery:
        locator = InMemoryCardSourceLocator(self.notes, self.cards)
        return CardSourceQuery(
            self.sittings,
            self.review_events,
            locator,
            self.clock,
        )

    def dependency_overrides(
        self,
    ) -> dict[Callable[..., object], Callable[..., object]]:
        return {
            get_open_sitting_command: self.open_sitting,
            get_grade_card_command: self.grade_card,
            get_reject_card_command: self.reject_card,
            get_current_card_query: self.current_card,
            get_due_count_query: self.due_count,
            get_reveal_back_command: self.reveal_back,
            get_card_source_query: self.card_source,
        }
