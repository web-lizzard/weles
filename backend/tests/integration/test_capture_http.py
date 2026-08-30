import json
from collections.abc import Iterator
from typing import Protocol, cast
from uuid import UUID

from fastapi.testclient import TestClient


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
