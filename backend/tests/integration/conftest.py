from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adapters.http.capture import router as capture_router
from adapters.http.outbox import router as outbox_router
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from main import app

from .support.in_memory_capture import InMemoryCaptureComposition


def _capture_routes_registered(application: FastAPI) -> bool:
    return any(
        getattr(route, "path", None) == "/capture-sessions"
        for route in application.routes
    )


def _outbox_routes_registered(application: FastAPI) -> bool:
    return any(
        getattr(route, "path", None) == "/_outbox" for route in application.routes
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
