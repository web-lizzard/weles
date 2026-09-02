"""Step definitions for vocabulary reuse acceptance scenarios."""

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Protocol, cast
from uuid import UUID

import pytest
from bdd.steps.capture import CaptureFlowContext
from fastapi.testclient import TestClient
from pytest_bdd import parsers, then, when


class SseResponse(Protocol):
    def iter_lines(self) -> Iterator[str]: ...


@dataclass
class VocabularyReuseContext:
    first_session_events: list[dict[str, object]] = field(default_factory=list)
    second_session_events: list[dict[str, object]] = field(default_factory=list)


@pytest.fixture
def vocabulary_reuse_context() -> VocabularyReuseContext:
    return VocabularyReuseContext()


@when(
    parsers.parse(
        'the user starts and completes a capture session about "{topic}" '
        + 'explaining "{explanation}"'
    )
)
def user_completes_a_capture_session(
    capture_flow_context: CaptureFlowContext,
    vocabulary_reuse_context: VocabularyReuseContext,
    topic: str,
    explanation: str,
) -> None:
    vocabulary_reuse_context.first_session_events = _run_capture_session(
        capture_flow_context, topic, explanation
    )


@when(
    parsers.parse(
        'the user starts and completes another capture session about "{topic}" '
        + 'explaining "{explanation}"'
    )
)
def user_completes_another_capture_session(
    capture_flow_context: CaptureFlowContext,
    vocabulary_reuse_context: VocabularyReuseContext,
    topic: str,
    explanation: str,
) -> None:
    vocabulary_reuse_context.second_session_events = _run_capture_session(
        capture_flow_context, topic, explanation
    )


@then("the drafted topic is marked as newly minted")
def drafted_topic_is_newly_minted(
    vocabulary_reuse_context: VocabularyReuseContext,
) -> None:
    draft_topic, _ = _draft_topic_and_tag_events(
        vocabulary_reuse_context.first_session_events
    )
    assert draft_topic["reused"] is False


@then("the drafted tags are all marked as newly minted")
def drafted_tags_are_newly_minted(
    vocabulary_reuse_context: VocabularyReuseContext,
) -> None:
    _, draft_tags = _draft_topic_and_tag_events(
        vocabulary_reuse_context.first_session_events
    )
    assert draft_tags
    assert all(tag["reused"] is False for tag in draft_tags)


@then("the second session's drafted topic is marked as reused")
def second_session_drafted_topic_is_reused(
    vocabulary_reuse_context: VocabularyReuseContext,
) -> None:
    draft_topic, _ = _draft_topic_and_tag_events(
        vocabulary_reuse_context.second_session_events
    )
    assert draft_topic["reused"] is True


@then("the second session's drafted tags are all marked as reused")
def second_session_drafted_tags_are_reused(
    vocabulary_reuse_context: VocabularyReuseContext,
) -> None:
    _, draft_tags = _draft_topic_and_tag_events(
        vocabulary_reuse_context.second_session_events
    )
    assert draft_tags
    assert all(tag["reused"] is True for tag in draft_tags)


def _collect_sse_events(response: SseResponse) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for line in response.iter_lines():
        if line.startswith("data: "):
            parsed = cast(dict[str, object], json.loads(line.removeprefix("data: ")))
            events.append(parsed)
    return events


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


def _run_capture_session(
    capture_flow_context: CaptureFlowContext, topic: str, explanation: str
) -> list[dict[str, object]]:
    assert capture_flow_context.client is not None
    session_id = _start_session(capture_flow_context.client)
    _ = _send_message(capture_flow_context.client, session_id, topic)
    _ = _send_message(capture_flow_context.client, session_id, explanation)
    return _send_message(capture_flow_context.client, session_id, "that's all")


def _draft_topic_and_tag_events(
    events: list[dict[str, object]],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    draft_topic = next(event for event in events if event["type"] == "draft_topic")
    draft_tags = [event for event in events if event["type"] == "draft_tag"]
    return draft_topic, draft_tags
