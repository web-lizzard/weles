import json
from collections.abc import AsyncIterator, Iterator
from typing import Protocol, cast
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from adapters.http.capture import router as capture_router
from adapters.out.in_memory.capture.reply_generation import (
    DeterministicReplyGenerationAdapter,
)
from application.capture.value_objects import (
    ConfidenceAssessment,
    ReplyChunk,
    ReplyTextChunk,
    Transcript,
)
from domain.capture.exceptions import CaptureSessionClosedError
from main import app

from .support.in_memory_capture import InMemoryCaptureComposition


class SseResponse(Protocol):
    def iter_lines(self) -> Iterator[str]: ...


def _create_session(client: TestClient) -> UUID:
    response = client.post("/capture-sessions")
    assert response.status_code == 200
    payload = cast(dict[str, object], response.json())
    session_id = payload["session_id"]
    assert isinstance(session_id, str)
    return UUID(session_id)


def _collect_sse_events(response: SseResponse) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for line in response.iter_lines():
        if line.startswith("data: "):
            parsed = cast(dict[str, object], json.loads(line.removeprefix("data: ")))
            events.append(parsed)
    return events


def test_create_capture_session_returns_a_valid_uuid(
    capture_client: TestClient,
) -> None:
    session_id = _create_session(capture_client)
    assert isinstance(session_id, UUID)


def test_first_message_streams_deltas_then_done_with_topic(
    capture_client: TestClient,
) -> None:
    session_id = _create_session(capture_client)

    with capture_client.stream(
        "POST",
        f"/capture-sessions/{session_id}/messages",
        json={"content": "I want to talk through how TCP handshakes work"},
    ) as response:
        assert response.status_code == 200
        events = _collect_sse_events(cast(SseResponse, response))

    assert any(event["type"] == "delta" for event in events)
    done_events = [event for event in events if event["type"] == "done"]
    assert len(done_events) == 1
    assert done_events[0]["topic"]


def test_second_message_keeps_the_session_topic(capture_client: TestClient) -> None:
    session_id = _create_session(capture_client)

    with capture_client.stream(
        "POST",
        f"/capture-sessions/{session_id}/messages",
        json={"content": "I want to talk through how TCP handshakes work"},
    ) as first_response:
        assert first_response.status_code == 200
        first_events = _collect_sse_events(cast(SseResponse, first_response))

    first_topic = next(
        event["topic"] for event in first_events if event["type"] == "done"
    )

    with capture_client.stream(
        "POST",
        f"/capture-sessions/{session_id}/messages",
        json={"content": "What happens during the third step?"},
    ) as second_response:
        assert second_response.status_code == 200
        second_events = _collect_sse_events(cast(SseResponse, second_response))

    second_done = next(event for event in second_events if event["type"] == "done")
    assert second_done["topic"] == first_topic


def test_unknown_session_returns_clean_404_before_streaming(
    capture_client: TestClient,
) -> None:
    unknown_session_id = UUID("00000000-0000-4000-8000-000000000001")
    response = capture_client.post(
        f"/capture-sessions/{unknown_session_id}/messages",
        json={"content": "Hello"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "capture_session_not_found"


def test_empty_message_content_returns_clean_422_before_streaming(
    capture_client: TestClient,
) -> None:
    session_id = _create_session(capture_client)
    response = capture_client.post(
        f"/capture-sessions/{session_id}/messages",
        json={"content": "   "},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "empty_message_content"


class _OneChunkThenFailReplyGeneration:
    async def generate(
        self,
        transcript: Transcript,
        assessment: ConfidenceAssessment,
    ) -> AsyncIterator[ReplyChunk]:
        _ = transcript
        _ = assessment
        yield ReplyTextChunk(text="partial")
        raise CaptureSessionClosedError


def _capture_routes_registered(application: FastAPI) -> bool:
    return any(
        getattr(route, "path", None) == "/capture-sessions"
        for route in application.routes
    )


def _assert_drafting_sse_sequence(events: list[dict[str, object]]) -> None:
    event_types = [str(event["type"]) for event in events]

    draft_topic_index = event_types.index("draft_topic")
    assert draft_topic_index >= 1
    assert all(event_type == "delta" for event_type in event_types[:draft_topic_index])

    draft_done_index = event_types.index("draft_done")
    done_index = event_types.index("done")
    assert done_index == len(event_types) - 1
    assert draft_done_index < done_index

    draft_delta_indices = [
        index
        for index, event_type in enumerate(event_types)
        if event_type == "draft_delta"
    ]
    first_draft_delta_index = (
        draft_delta_indices[0] if draft_delta_indices else draft_done_index
    )
    middle_types = event_types[draft_topic_index + 1 : first_draft_delta_index]
    assert all(event_type == "draft_tag" for event_type in middle_types)

    if draft_delta_indices:
        assert all(
            event_type == "draft_delta"
            for event_type in event_types[first_draft_delta_index:draft_done_index]
        )


def test_confirmation_turn_streams_draft_events_then_done(
    capture_client: TestClient,
) -> None:
    session_id = _create_session(capture_client)

    with capture_client.stream(
        "POST",
        f"/capture-sessions/{session_id}/messages",
        json={"content": "How TCP handshakes work"},
    ) as first_response:
        assert first_response.status_code == 200
        _ = _collect_sse_events(cast(SseResponse, first_response))

    with capture_client.stream(
        "POST",
        f"/capture-sessions/{session_id}/messages",
        json={"content": "The client sends SYN and the server replies SYN-ACK"},
    ) as second_response:
        assert second_response.status_code == 200
        _ = _collect_sse_events(cast(SseResponse, second_response))

    with capture_client.stream(
        "POST",
        f"/capture-sessions/{session_id}/messages",
        json={"content": "that's all"},
    ) as draft_response:
        assert draft_response.status_code == 200
        events = _collect_sse_events(cast(SseResponse, draft_response))

    _assert_drafting_sse_sequence(events)

    draft_done = next(event for event in events if event["type"] == "draft_done")
    assert draft_done["note_id"]
    assert str(draft_done["topic"]).strip() != ""
    assert str(draft_done["content"]).strip() != ""
    tags = draft_done["tags"]
    assert isinstance(tags, list) and tags


def test_core_exception_during_generation_yields_in_band_error_event() -> None:
    if not _capture_routes_registered(app):
        app.include_router(capture_router)

    composition = InMemoryCaptureComposition.create()
    composition.reply_generation = cast(
        DeterministicReplyGenerationAdapter,
        cast(object, _OneChunkThenFailReplyGeneration()),
    )
    app.dependency_overrides.update(composition.dependency_overrides())
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            session_id = _create_session(client)

            with client.stream(
                "POST",
                f"/capture-sessions/{session_id}/messages",
                json={"content": "Hello"},
            ) as response:
                assert response.status_code == 200
                events = _collect_sse_events(cast(SseResponse, response))
    finally:
        app.dependency_overrides.clear()

    assert len(events) == 2
    assert events[0]["type"] == "delta"
    assert events[1]["type"] == "error"
    assert events[1]["code"] == CaptureSessionClosedError.code()
    assert events[1]["detail"]
