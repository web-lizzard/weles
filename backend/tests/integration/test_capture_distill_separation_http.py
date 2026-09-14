# pyright: reportPrivateUsage=false

from typing import cast

import pytest
from fastapi.testclient import TestClient

from adapters.auth.router import require_sign_in
from adapters.compose import (
    get_list_cards_for_note_query,
    get_list_notes_query,
    get_note_query,
)
from adapters.http.capture import router as capture_router
from adapters.http.notes import router as notes_router
from adapters.out.in_memory.distill.get_note_query import InMemoryGetNoteQueryAdapter
from adapters.out.in_memory.distill.list_cards_for_note_query import (
    InMemoryListCardsForNoteQueryAdapter,
)
from adapters.out.in_memory.distill.list_notes_query import (
    InMemoryListNotesQueryAdapter,
)
from adapters.out.in_memory.shared.outbox.appender import InMemoryOutboxAppender
from adapters.out.in_memory.shared.outbox.envelope_query import (
    InMemoryOutboxEnvelopeQueryAdapter,
)
from adapters.out.in_memory.shared.outbox.store import InMemoryOutboxStore
from adapters.out.worker.outbox_worker import OutboxWorker
from domain.shared.identity.model import UserId
from main import app

from .conftest import _capture_routes_registered, _notes_routes_registered
from .support.in_memory_capture import InMemoryCaptureComposition
from .support.in_memory_distill import InMemoryDistillComposition
from .test_capture_http import _draft_note_in_new_session, _SwitchableSignInGate


async def _drain_distill_worker(worker: OutboxWorker) -> None:
    while True:
        acked = await worker.run_once()
        if acked == 0:
            return


@pytest.mark.asyncio
async def test_person_b_gets_empty_notes_and_404_after_a_approves_and_worker_runs() -> (
    None
):
    if not _capture_routes_registered(app):
        app.include_router(capture_router)
    if not _notes_routes_registered(app):
        app.include_router(notes_router)

    outbox_store = InMemoryOutboxStore()
    capture = InMemoryCaptureComposition.create()
    capture.outbox_store = outbox_store
    capture.outbox = InMemoryOutboxAppender(outbox_store)
    capture.outbox_query = InMemoryOutboxEnvelopeQueryAdapter(outbox_store)
    distill = InMemoryDistillComposition.create(outbox_store)

    notes_query = InMemoryListNotesQueryAdapter(distill.notes, distill.cards)
    note_query = InMemoryGetNoteQueryAdapter(distill.notes)
    cards_query = InMemoryListCardsForNoteQueryAdapter(distill.notes, distill.cards)

    person_a = UserId.new()
    person_b = UserId.new()
    gate = _SwitchableSignInGate(person_a)

    app.dependency_overrides.update(capture.dependency_overrides())
    app.dependency_overrides[get_list_notes_query] = lambda: notes_query
    app.dependency_overrides[get_note_query] = lambda: note_query
    app.dependency_overrides[get_list_cards_for_note_query] = lambda: cards_query
    app.dependency_overrides[require_sign_in] = gate

    try:
        with TestClient(app) as client:
            session_id, _events = _draft_note_in_new_session(client)
            approval = client.post(f"/capture-sessions/{session_id}/approval")
            assert approval.status_code == 200
            note_id = cast(dict[str, object], approval.json())["note_id"]
            assert isinstance(note_id, str)

            await _drain_distill_worker(distill.worker())

            gate.act_as(person_b)

            list_response = client.get("/notes")
            assert list_response.status_code == 200
            assert list_response.json() == []

            detail_response = client.get(f"/notes/{note_id}")
            assert detail_response.status_code == 404
            assert detail_response.json()["code"] == "distill_note_not_found"

            cards_response = client.get(f"/notes/{note_id}/cards")
            assert cards_response.status_code == 404
            assert cards_response.json()["code"] == "distill_note_not_found"

            gate.act_as(person_a)

            owner_list = client.get("/notes")
            assert owner_list.status_code == 200
            owner_notes = cast(list[dict[str, object]], owner_list.json())
            assert len(owner_notes) == 1
            assert owner_notes[0]["note_id"] == note_id
            card_count = owner_notes[0]["card_count"]
            assert isinstance(card_count, int) and card_count > 0

            owner_cards = client.get(f"/notes/{note_id}/cards")
            assert owner_cards.status_code == 200
            assert cast(list[object], owner_cards.json())
    finally:
        app.dependency_overrides.clear()
