# Property test review r4

ran at d295ddb

- **change-id**: capture-flow-socratic-conversation
- **scope**: phase 6
- **engine**: Hypothesis 6.165.10 + pytest (per `context/foundation/test-stack.md`)
- **oracle-able surface**:
  - `backend/src/application/capture/commands/start_capture_session.py`
  - `backend/src/application/capture/commands/send_message.py`
- **properties hunted**:
  - StartCaptureSessionCommand round-trip: returned id identifies a persisted OPEN session with no topic
  - load_open_session_for_turn canonicalizes padded content to stripped form
  - GenerateReplyCommand stream integrity: `ReplyDoneEvent.content` equals concatenation of delta texts; exactly one done event last
  - Completed turn adds exactly two messages (user then agent) with matching content
  - Partial consumption (stop before `ReplyDoneEvent`) rolls back — no messages, no topic
  - Second turn preserves pre-assigned topic in done event
  - Persisted topic survives when in-memory session carries `topic=None` but repository already assigned one
  - Empty reply stream does not commit partial state
- **budget**: `max_examples=200` per property, `deadline=None`
- **date**: 2026-08-31

## Specimens

### R4-F1 — WARNING

- **Property**: When persistence already records a topic for the session id, completing a turn must not replace it with a newly extracted topic.
- **Shrunk input**: stale in-memory `CaptureSession` with `topic=None` while repository holds `Topic("Persisted topic")`; turn content `"0"`
- **Replay**: Hypothesis `seed=1` (`HYPOTHESIS_SEED=1` or `@seed(1)`); failing draw `raw='0'`
- **Proposed pin**:

```python
async def test_R4_F1_stale_session_does_not_overwrite_persisted_topic() -> None:
    stack = _make_command_stack()
    session = CaptureSession.start()
    session.assign_topic(Topic(value="Persisted topic"))
    await stack.session_repo.save(session)

    stale = CaptureSession(
        id=session.id,
        topic=None,
        status=session.status,
        created_at=session.created_at,
    )
    content = MessageContent(value="0")

    events = [event async for event in stack.command.handle(stale, content)]
    done = next(event for event in events if isinstance(event, ReplyDoneEvent))

    persisted = await stack.session_repo.get(session.id)
    assert persisted is not None
    assert persisted.topic is not None
    assert persisted.topic.value == "Persisted topic"
    assert done.topic == "Persisted topic"
```

- **Proof**: `proof-test skipped: HEAD on default branch`
- **Fix:** `"0"` with a stale `topic=None` in-memory session must fail `test_R4_F1_stale_session_does_not_overwrite_persisted_topic` until `GenerateReplyCommand` guards topic assignment against an already-persisted topic, then remain as regression.

## Classified (not triaged)

- **Early close after full drain** — property too strong. Consuming every event including `ReplyDoneEvent` is a successful turn; expecting rollback conflates partial consumption with full drain.
- **R3-F1 (ReplyDoneEvent inside `async with`)** — already open triage row `6.6`; structural drift, not a new behavioral edge from this hunt.

## Retractions

None.

## No new edge found

(n/a — one specimen queued)
