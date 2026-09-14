# pyright: reportPrivateUsage=false

from typing import cast

import pytest
from fastapi.testclient import TestClient

from adapters.auth.router import require_sign_in
from adapters.http.capture import router as capture_router
from adapters.http.remember import router as remember_router
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.envelope_query import (
    InMemoryOutboxEnvelopeQueryAdapter,
)
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from adapters.out.worker.outbox_worker import OutboxWorker
from domain.shared.identity.model import UserId
from main import app

from .conftest import _capture_routes_registered, _remember_routes_registered
from .support.in_memory_capture import InMemoryCaptureComposition
from .support.in_memory_distill import InMemoryDistillComposition
from .support.in_memory_remember import InMemoryRememberComposition
from .test_capture_http import _draft_note_in_new_session, _SwitchableSignInGate


async def _drain_worker(worker: OutboxWorker) -> None:
    while True:
        acked = await worker.run_once()
        if acked == 0:
            return


@pytest.mark.asyncio
async def test_person_b_cannot_touch_person_a_review_after_capture_approval() -> None:
    if not _capture_routes_registered(app):
        app.include_router(capture_router)
    if not _remember_routes_registered(app):
        app.include_router(remember_router)

    outbox_store = InMemoryOutboxStore()
    capture = InMemoryCaptureComposition.create()
    capture.outbox_store = outbox_store
    capture.outbox = InMemoryOutboxAppender(outbox_store)
    capture.outbox_query = InMemoryOutboxEnvelopeQueryAdapter(outbox_store)
    distill = InMemoryDistillComposition.create(outbox_store)
    remember = InMemoryRememberComposition.create(
        notes=distill.notes,
        cards=distill.cards,
        outbox_store=outbox_store,
    )

    person_a = UserId.new()
    person_b = UserId.new()
    gate = _SwitchableSignInGate(person_a)

    app.dependency_overrides.update(capture.dependency_overrides())
    app.dependency_overrides.update(remember.dependency_overrides())
    app.dependency_overrides[require_sign_in] = gate

    try:
        with TestClient(app) as client:
            session_id, _events = _draft_note_in_new_session(client)
            approval = client.post(f"/capture-sessions/{session_id}/approval")
            assert approval.status_code == 200

            await _drain_worker(distill.worker())

            opened = client.post("/review-sittings")
            assert opened.status_code == 200
            opened_body = cast(dict[str, object], opened.json())
            assert opened_body["kind"] in ("opened", "resumed")
            sitting_id = cast(str, opened_body["sitting_id"])
            card_id = cast(str, opened_body["card_id"])

            gate.act_as(person_b)

            due = client.get("/due-cards/count")
            assert due.status_code == 200
            due_partition = cast(dict[str, object], due.json()["due"])
            assert due_partition["total"] == 0

            nothing_due = client.post("/review-sittings")
            assert nothing_due.status_code == 200
            assert nothing_due.json() == {"kind": "nothing_due"}

            current = client.get(f"/review-sittings/{sitting_id}/current-card")
            assert current.status_code == 404
            assert current.json()["code"] == "sitting_not_found"

            back = client.post(
                f"/review-sittings/{sitting_id}/cards/{card_id}/back",
            )
            assert back.status_code == 404
            assert back.json()["code"] == "sitting_not_found"

            source = client.get(
                f"/review-sittings/{sitting_id}/cards/{card_id}/source",
            )
            assert source.status_code == 404
            assert source.json()["code"] == "sitting_not_found"

            grade = client.post(
                f"/review-sittings/{sitting_id}/cards/{card_id}/grade",
                json={"grade": "good"},
            )
            assert grade.status_code == 404
            assert grade.json()["code"] == "sitting_not_found"

            rejection = client.post(
                f"/review-sittings/{sitting_id}/cards/{card_id}/rejection",
            )
            assert rejection.status_code == 404
            assert rejection.json()["code"] == "sitting_not_found"

            gate.act_as(person_a)

            owner_grade = client.post(
                f"/review-sittings/{sitting_id}/cards/{card_id}/grade",
                json={"grade": "good"},
            )
            assert owner_grade.status_code == 200
            graded_body = cast(dict[str, object], owner_grade.json())
            assert graded_body["sitting_complete"] is True
    finally:
        app.dependency_overrides.clear()
