import asyncio
from collections.abc import Iterator
from dataclasses import dataclass
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adapters.compose import (
    get_current_card_query,
    get_grade_card_command,
    get_list_cards_for_note_query,
    get_list_notes_query,
    get_note_query,
    get_open_sitting_command,
    get_reveal_back_query,
)
from adapters.http.capture import router as capture_router
from adapters.http.notes import router as notes_router
from adapters.http.outbox import router as outbox_router
from adapters.http.remember import router as remember_router
from adapters.out.fsrs.scheduler import FsrsScheduler
from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.get_note_query import InMemoryGetNoteQueryAdapter
from adapters.out.in_memory.distill.list_cards_for_note_query import (
    InMemoryListCardsForNoteQueryAdapter,
)
from adapters.out.in_memory.distill.list_notes_query import (
    InMemoryListNotesQueryAdapter,
)
from adapters.out.in_memory.distill.note_repository import (
    InMemoryNoteRepository as InMemoryDistillNoteRepository,
)
from adapters.out.in_memory.remember.clock import SystemClock
from adapters.out.in_memory.remember.review_catalog import InMemoryReviewCatalog
from adapters.out.in_memory.remember.review_event_store import InMemoryReviewEventStore
from adapters.out.in_memory.remember.scheduling_state_repository import (
    InMemorySchedulingStateRepository,
)
from adapters.out.in_memory.remember.sitting_repository import InMemorySittingRepository
from adapters.out.in_memory.remember.unit_of_work import (
    InMemoryUnitOfWork as InMemoryRememberUnitOfWork,
)
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from application.remember.commands.grade_card import GradeCardCommand
from application.remember.commands.open_sitting import OpenSittingCommand
from application.remember.ports import UnitOfWork as RememberUnitOfWork
from application.remember.queries.current_card import CurrentCardQuery
from application.remember.queries.reveal_back import RevealBackQuery
from domain.remember.value_objects import ShowingLimit
from main import app

from .support.in_memory_capture import InMemoryCaptureComposition

_REMEMBER_SHOWING_LIMIT = 2


def _capture_routes_registered(application: FastAPI) -> bool:
    return any(
        getattr(route, "path", None) == "/capture-sessions"
        for route in application.routes
    )


def _outbox_routes_registered(application: FastAPI) -> bool:
    return any(
        getattr(route, "path", None) == "/_outbox" for route in application.routes
    )


def _notes_routes_registered(application: FastAPI) -> bool:
    return any(getattr(route, "path", None) == "/notes" for route in application.routes)


def _remember_routes_registered(application: FastAPI) -> bool:
    return any(
        getattr(route, "path", None) == "/review-sittings"
        for route in application.routes
    )


@pytest.fixture
def capture_client() -> Iterator[TestClient]:
    if not _capture_routes_registered(app):
        app.include_router(capture_router)

    composition = InMemoryCaptureComposition.create()
    app.dependency_overrides.update(composition.dependency_overrides())
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@dataclass
class OutboxTestContext:
    client: TestClient
    outbox_store: InMemoryOutboxStore


@pytest.fixture
def outbox_client() -> Iterator[OutboxTestContext]:
    if not _capture_routes_registered(app):
        app.include_router(capture_router)
    if not _outbox_routes_registered(app):
        app.include_router(outbox_router)

    composition = InMemoryCaptureComposition.create()
    app.dependency_overrides.update(composition.dependency_overrides())
    with TestClient(app) as client:
        yield OutboxTestContext(client=client, outbox_store=composition.outbox_store)
    app.dependency_overrides.clear()


@dataclass
class NotesTestContext:
    client: TestClient
    notes: InMemoryDistillNoteRepository
    cards: InMemoryCardRepository


@pytest.fixture
def notes_client() -> Iterator[NotesTestContext]:
    if not _notes_routes_registered(app):
        app.include_router(notes_router)

    notes = InMemoryDistillNoteRepository()
    cards = InMemoryCardRepository()
    query = InMemoryListNotesQueryAdapter(notes, cards)
    note_query = InMemoryGetNoteQueryAdapter(notes)
    cards_query = InMemoryListCardsForNoteQueryAdapter(notes, cards)
    app.dependency_overrides[get_list_notes_query] = lambda: query
    app.dependency_overrides[get_note_query] = lambda: note_query
    app.dependency_overrides[get_list_cards_for_note_query] = lambda: cards_query
    with TestClient(app) as client:
        yield NotesTestContext(client=client, notes=notes, cards=cards)
    app.dependency_overrides.clear()


@dataclass
class RememberTestContext:
    client: TestClient
    notes: InMemoryDistillNoteRepository
    cards: InMemoryCardRepository


@pytest.fixture
def remember_client() -> Iterator[RememberTestContext]:
    if not _remember_routes_registered(app):
        app.include_router(remember_router)

    notes = InMemoryDistillNoteRepository()
    cards = InMemoryCardRepository()
    catalog = InMemoryReviewCatalog(notes, cards)
    sittings = InMemorySittingRepository()
    review_events = InMemoryReviewEventStore()
    scheduling_states = InMemorySchedulingStateRepository()
    lock = asyncio.Lock()
    scheduler = FsrsScheduler()
    clock = SystemClock()
    showing_limit = ShowingLimit(value=_REMEMBER_SHOWING_LIMIT)

    def uow_factory() -> RememberUnitOfWork:
        return cast(
            RememberUnitOfWork,
            cast(
                object,
                InMemoryRememberUnitOfWork(
                    sittings, review_events, scheduling_states, lock
                ),
            ),
        )

    app.dependency_overrides[get_open_sitting_command] = lambda: OpenSittingCommand(
        uow_factory=uow_factory,
        catalog=catalog,
        clock=clock,
        showing_limit=showing_limit,
        scheduler=scheduler,
    )
    app.dependency_overrides[get_current_card_query] = lambda: CurrentCardQuery(
        sittings, review_events, catalog
    )
    app.dependency_overrides[get_reveal_back_query] = lambda: RevealBackQuery(
        sittings, catalog
    )
    app.dependency_overrides[get_grade_card_command] = lambda: GradeCardCommand(
        uow_factory=uow_factory, catalog=catalog, scheduler=scheduler, clock=clock
    )
    with TestClient(app) as client:
        yield RememberTestContext(client=client, notes=notes, cards=cards)
    app.dependency_overrides.clear()
