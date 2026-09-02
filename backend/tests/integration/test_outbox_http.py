import importlib
from typing import cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import main as main_module
from adapters.out.in_memory.shared.outbox.claimer import InMemoryOutboxClaimer
from adapters.out.worker.outbox_worker import OutboxWorker
from domain.capture.outbox import NOTE_APPROVED
from domain.shared.outbox.model import EnvelopeType, OutboxEnvelope

from .conftest import OutboxTestContext


class _NoOpHandler:
    envelope_type: EnvelopeType = NOTE_APPROVED

    async def handle(self, envelope: OutboxEnvelope) -> None:
        del envelope


async def test_outbox_endpoint_lists_envelope_and_reflects_status_after_run_once(
    outbox_client: OutboxTestContext,
) -> None:
    envelope = OutboxEnvelope.pending(NOTE_APPROVED, {"note_id": str(uuid4())})
    await outbox_client.outbox_store.put(envelope)

    listed_before = cast(
        list[dict[str, object]], outbox_client.client.get("/_outbox").json()
    )
    assert len(listed_before) == 1
    assert listed_before[0]["type"] == "note_approved@1"
    assert listed_before[0]["status"] == "pending"

    claimer = InMemoryOutboxClaimer(outbox_client.outbox_store)
    worker = OutboxWorker(
        claimer,
        [_NoOpHandler()],
        worker_id="test-worker",
        batch_size=10,
        max_attempts=3,
    )
    acked = await worker.run_once()
    assert acked == 1

    listed_after = cast(
        list[dict[str, object]], outbox_client.client.get("/_outbox").json()
    )
    assert listed_after[0]["status"] == "consumed"


def test_outbox_route_is_registered_and_documented_outside_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ENVIRONMENT_NAME", raising=False)
    _ = importlib.reload(main_module)
    try:
        openapi_paths = cast(dict[str, object], main_module.app.openapi()["paths"])
        assert "/_outbox" in openapi_paths
    finally:
        _ = importlib.reload(main_module)


def test_outbox_route_is_absent_and_undocumented_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT_NAME", "prod")
    _ = importlib.reload(main_module)
    try:
        with TestClient(main_module.app) as client:
            response = client.get("/_outbox")
            assert response.status_code == 404
        openapi_paths = cast(dict[str, object], main_module.app.openapi()["paths"])
        assert "/_outbox" not in openapi_paths
    finally:
        monkeypatch.delenv("ENVIRONMENT_NAME", raising=False)
        _ = importlib.reload(main_module)
