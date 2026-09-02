"""Step definitions for capture-flow acceptance scenarios."""

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Protocol, cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, then, when


class SseResponse(Protocol):
    def iter_lines(self) -> Iterator[str]: ...


@dataclass
class CaptureFlowContext:
    client: TestClient | None = None
    session_id: UUID | None = None
    topic: str | None = None
    latest_user_message: str | None = None
    reply_events: list[dict[str, object]] = field(default_factory=list)
    reply_text: str = ""
    draft_done_history: list[dict[str, object]] = field(default_factory=list)


@pytest.fixture
def capture_flow_context() -> CaptureFlowContext:
    return CaptureFlowContext()


def _collect_sse_events(response: SseResponse) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for line in response.iter_lines():
        if line.startswith("data: "):
            parsed = cast(dict[str, object], json.loads(line.removeprefix("data: ")))
            events.append(parsed)
    return events


def _reply_text_from_events(events: list[dict[str, object]]) -> str:
    delta_text = "".join(
        str(event["text"]) for event in events if event["type"] == "delta"
    )
    done_events = [event for event in events if event["type"] == "done"]
    if done_events:
        return str(done_events[0]["content"])
    return delta_text


def _start_session(client: TestClient) -> UUID:
    response = client.post("/capture-sessions")
    assert response.status_code == 200
    payload = cast(dict[str, object], response.json())
    session_id = payload["session_id"]
    assert isinstance(session_id, str)
    return UUID(session_id)


def _send_message(
    client: TestClient, session_id: UUID, content: str
) -> list[dict[str, object]]:
    with client.stream(
        "POST",
        f"/capture-sessions/{session_id}/messages",
        json={"content": content},
    ) as response:
        assert response.status_code == 200
        return _collect_sse_events(cast(SseResponse, response))


@given("a running capture backend")
def running_capture_backend(
    capture_client: TestClient, capture_flow_context: CaptureFlowContext
) -> None:
    capture_flow_context.client = capture_client


@when("the user starts a capture session")
def user_starts_capture_session(capture_flow_context: CaptureFlowContext) -> None:
    assert capture_flow_context.client is not None
    capture_flow_context.session_id = _start_session(capture_flow_context.client)


@when(parsers.parse('the user names the topic "{topic}"'))
def user_names_topic(capture_flow_context: CaptureFlowContext, topic: str) -> None:
    assert capture_flow_context.client is not None
    assert capture_flow_context.session_id is not None
    events = _send_message(
        capture_flow_context.client, capture_flow_context.session_id, topic
    )
    capture_flow_context.reply_events = events
    capture_flow_context.reply_text = _reply_text_from_events(events)
    done = next(event for event in events if event["type"] == "done")
    capture_flow_context.topic = str(done["topic"])


@given(parsers.parse('the user has started a capture session with topic "{topic}"'))
def user_started_session_with_topic(
    capture_flow_context: CaptureFlowContext, topic: str
) -> None:
    assert capture_flow_context.client is not None
    session_id = _start_session(capture_flow_context.client)
    events = _send_message(capture_flow_context.client, session_id, topic)
    done = next(event for event in events if event["type"] == "done")
    capture_flow_context.session_id = session_id
    capture_flow_context.topic = str(done["topic"])
    capture_flow_context.reply_events = events
    capture_flow_context.reply_text = _reply_text_from_events(events)


@when(parsers.parse('the user says "{message}"'))
def user_says_message(capture_flow_context: CaptureFlowContext, message: str) -> None:
    assert capture_flow_context.client is not None
    assert capture_flow_context.session_id is not None
    events = _send_message(
        capture_flow_context.client, capture_flow_context.session_id, message
    )
    capture_flow_context.latest_user_message = message
    capture_flow_context.reply_events = events
    capture_flow_context.reply_text = _reply_text_from_events(events)
    capture_flow_context.draft_done_history.extend(
        event for event in events if event["type"] == "draft_done"
    )


@then(parsers.parse('the session topic is set to "{expected_topic}"'))
def session_topic_is_set(
    capture_flow_context: CaptureFlowContext, expected_topic: str
) -> None:
    assert capture_flow_context.topic == expected_topic


@then("the agent reply probes understanding with a follow-up question")
def agent_reply_probes_understanding(capture_flow_context: CaptureFlowContext) -> None:
    reply = capture_flow_context.reply_text
    assert "Let's dig into:" in reply
    assert capture_flow_context.latest_user_message is not None
    assert reply.strip() != capture_flow_context.latest_user_message.strip()


@then("the agent reply acknowledges what seems solid")
def agent_reply_acknowledges_solid(capture_flow_context: CaptureFlowContext) -> None:
    assert "You've got a handle on:" in capture_flow_context.reply_text


@then("the agent reply flags what seems shaky")
def agent_reply_flags_shaky(capture_flow_context: CaptureFlowContext) -> None:
    assert "Let's dig into:" in capture_flow_context.reply_text


@then("the agent follow-up targets the shaky part of the latest user message")
def agent_follow_up_targets_shaky_part(
    capture_flow_context: CaptureFlowContext,
) -> None:
    assert capture_flow_context.latest_user_message is not None
    shaky_note = (
        f"The details behind: {capture_flow_context.latest_user_message.strip()}"
    )
    reply = capture_flow_context.reply_text
    assert "Let's dig into:" in reply
    assert shaky_note in reply
