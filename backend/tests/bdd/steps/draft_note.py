"""Step definitions for draft-note acceptance scenarios."""

from bdd.steps.capture import CaptureFlowContext
from pytest_bdd import then


@then("the draft note has a topic, body, and at least one tag")
def draft_note_has_topic_body_and_tags(
    capture_flow_context: CaptureFlowContext,
) -> None:
    draft_done = next(
        event
        for event in capture_flow_context.reply_events
        if event["type"] == "draft_done"
    )
    assert str(draft_done["topic"]).strip() != ""
    assert str(draft_done["content"]).strip() != ""
    tags = draft_done["tags"]
    assert isinstance(tags, list) and tags


@then("the drafted topic label differs from the session topic")
def drafted_topic_differs_from_session_topic(
    capture_flow_context: CaptureFlowContext,
) -> None:
    assert capture_flow_context.topic is not None
    draft_done = next(
        event
        for event in capture_flow_context.reply_events
        if event["type"] == "draft_done"
    )
    assert str(draft_done["topic"]) != capture_flow_context.topic
