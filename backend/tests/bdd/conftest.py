"""Shared fixtures for acceptance tests."""

from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from integration.support.in_memory_capture import (  # pyright: ignore[reportImplicitRelativeImport]
    InMemoryCaptureComposition,
)
from integration.support.in_memory_distill import (  # pyright: ignore[reportImplicitRelativeImport]
    InMemoryDistillComposition,
)

from adapters.compose import get_list_notes_query
from adapters.http.capture import router as capture_router
from adapters.http.notes import router as notes_router
from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.list_notes_query import (
    InMemoryListNotesQueryAdapter,
)
from adapters.out.in_memory.distill.note_repository import (
    InMemoryNoteRepository as InMemoryDistillNoteRepository,
)
from main import app


def _capture_routes_registered(application: FastAPI) -> bool:
    return any(
        getattr(route, "path", None) == "/capture-sessions"
        for route in application.routes
    )


def _notes_routes_registered(application: FastAPI) -> bool:
    return any(getattr(route, "path", None) == "/notes" for route in application.routes)


@dataclass
class NotesTestContext:
    client: TestClient
    notes: InMemoryDistillNoteRepository
    cards: InMemoryCardRepository


@pytest.fixture
def capture_composition() -> Iterator[InMemoryCaptureComposition]:
    yield InMemoryCaptureComposition.create()


@pytest.fixture
def capture_client(
    capture_composition: InMemoryCaptureComposition,
) -> Iterator[TestClient]:
    if not _capture_routes_registered(app):
        app.include_router(capture_router)

    app.dependency_overrides.update(capture_composition.dependency_overrides())
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def distill_composition(
    capture_composition: InMemoryCaptureComposition,
) -> Iterator[InMemoryDistillComposition]:
    yield InMemoryDistillComposition.create(capture_composition.outbox_store)


@pytest.fixture
def notes_client() -> Iterator[NotesTestContext]:
    if not _notes_routes_registered(app):
        app.include_router(notes_router)

    notes = InMemoryDistillNoteRepository()
    cards = InMemoryCardRepository()
    query = InMemoryListNotesQueryAdapter(notes, cards)
    app.dependency_overrides[get_list_notes_query] = lambda: query
    with TestClient(app) as client:
        yield NotesTestContext(client=client, notes=notes, cards=cards)
    app.dependency_overrides.clear()
