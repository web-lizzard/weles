from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adapters.compose import (
    get_list_cards_for_note_query,
    get_list_notes_query,
    get_note_query,
)
from adapters.http.capture import router as capture_router
from adapters.http.notes import router as notes_router
from adapters.http.outbox import router as outbox_router
from adapters.http.remember import router as remember_router
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
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from main import app

from .support.in_memory_capture import InMemoryCaptureComposition
from .support.in_memory_remember import InMemoryRememberComposition


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

    composition = InMemoryRememberComposition.create()
    app.dependency_overrides.update(composition.dependency_overrides())
    with TestClient(app) as client:
        yield RememberTestContext(
            client=client, notes=composition.notes, cards=composition.cards
        )
    app.dependency_overrides.clear()
