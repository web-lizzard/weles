"""Step definitions for redraft and approve-to-outbox acceptance scenarios."""

import asyncio
from dataclasses import dataclass
from typing import cast
from uuid import UUID

import pytest
from bdd.steps.capture import CaptureFlowContext
from integration.support.in_memory_capture import (
    InMemoryCaptureComposition,
)
from pytest_bdd import then, when

from domain.capture.value_objects import SessionId, SessionStatus


@dataclass
class ApproveOutboxContext:
    approval_response: dict[str, object] | None = None


@pytest.fixture
def approve_outbox_context() -> ApproveOutboxContext:
    return ApproveOutboxContext()


@when("the user approves the draft")
def user_approves_the_draft(
    capture_flow_context: CaptureFlowContext,
    approve_outbox_context: ApproveOutboxContext,
) -> None:
    assert capture_flow_context.client is not None
    assert capture_flow_context.session_id is not None
    response = capture_flow_context.client.post(
        f"/capture-sessions/{capture_flow_context.session_id}/approval"
    )
    assert response.status_code == 200
    approve_outbox_context.approval_response = cast(dict[str, object], response.json())


@then("no envelope has been queued to the outbox")
def no_envelope_queued(capture_composition: InMemoryCaptureComposition) -> None:
    assert capture_composition.outbox_store.all() == []


@then("exactly one envelope has been queued to the outbox")
def exactly_one_envelope_queued(
    capture_composition: InMemoryCaptureComposition,
) -> None:
    assert len(capture_composition.outbox_store.all()) == 1


@then("the approval response reports the note as approved")
def approval_response_reports_note_approved(
    approve_outbox_context: ApproveOutboxContext,
) -> None:
    assert approve_outbox_context.approval_response is not None
    assert UUID(str(approve_outbox_context.approval_response["note_id"]))
    assert str(approve_outbox_context.approval_response["topic"]).strip() != ""
    assert approve_outbox_context.approval_response["approved_at"] is not None


@then("the capture session is closed")
def capture_session_is_closed(
    capture_flow_context: CaptureFlowContext,
    capture_composition: InMemoryCaptureComposition,
) -> None:
    assert capture_flow_context.session_id is not None
    session = asyncio.run(
        capture_composition.capture_sessions.get(
            SessionId(value=capture_flow_context.session_id)
        )
    )
    assert session is not None
    assert session.status == SessionStatus.CLOSED


@then("the redraft keeps the same note id as the first draft")
def redraft_keeps_same_note_id(capture_flow_context: CaptureFlowContext) -> None:
    history = capture_flow_context.draft_done_history
    assert len(history) >= 2
    assert history[0]["note_id"] == history[-1]["note_id"]


@then("the redrafted content differs from the first draft")
def redrafted_content_differs(capture_flow_context: CaptureFlowContext) -> None:
    history = capture_flow_context.draft_done_history
    assert len(history) >= 2
    assert history[0]["content"] != history[-1]["content"]
