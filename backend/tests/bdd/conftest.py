"""Shared fixtures for acceptance tests."""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from integration.support.in_memory_capture import (  # pyright: ignore[reportImplicitRelativeImport]
    InMemoryCaptureComposition,
)

from adapters.http.capture import router as capture_router
from main import app


def _capture_routes_registered(application: FastAPI) -> bool:
    return any(
        getattr(route, "path", None) == "/capture-sessions"
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
