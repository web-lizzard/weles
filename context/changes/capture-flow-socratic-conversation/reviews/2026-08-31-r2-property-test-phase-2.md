# Property test review r2

ran at 185ce07

- **change-id**: capture-flow-socratic-conversation
- **scope**: phase 2
- **engine**: Hypothesis 6.165.10 + pytest (per `context/foundation/test-stack.md`)
- **oracle-able surface**:
  - `backend/src/domain/capture/value_objects.py`
  - `backend/src/domain/capture/capture_session.py`
  - `backend/src/domain/capture/message.py`
- **properties hunted**:
  - Validity oracle: constructibility iff non-empty stripped form and stripped length within cap
  - Canonical form: constructed string VOs store `strip(input)`, not raw padding/control suffixes
  - Raw buffer length bounded by cap when valid (differential)
  - `CaptureSession.start()` invariants (OPEN, no topic, UTC `created_at`)
  - `assign_topic` rejects second assignment
- **budget**: `max_examples=200` per property, `deadline=None`
- **date**: 2026-08-31

## Specimens

### R2-F1 — WARNING

- **Property**: A validated `Topic` stores its canonical stripped form (`value == value.strip()`), not the raw input bytes that passed validation.
- **Shrunk input**: `"0\r"`
- **Replay**: Hypothesis `seed=1` (`HYPOTHESIS_SEED=1` or `@seed(1)`); failing draw `raw='0\r'`
- **Proposed pin**:

```python
def test_R2_F1_topic_stores_canonical_stripped_value() -> None:
    topic = Topic(value="0\r")
    assert topic.value == "0"
```

- **Proof**: `proof-test skipped: HEAD on default branch`
- **Fix:** `"0\r"` must fail `test_R2_F1_topic_stores_canonical_stripped_value` until `Topic` normalizes on construction, then remain as regression.

### R2-F2 — WARNING

- **Property**: A validated `MessageContent` stores its canonical stripped form (`value == value.strip()`), not the raw input bytes that passed validation.
- **Shrunk input**: `"0\r"`
- **Replay**: Hypothesis `seed=1` (`HYPOTHESIS_SEED=1` or `@seed(1)`); failing draw `raw='0\r'`
- **Proposed pin**:

```python
def test_R2_F2_message_content_stores_canonical_stripped_value() -> None:
    content = MessageContent(value="0\r")
    assert content.value == "0"
```

- **Proof**: `proof-test skipped: HEAD on default branch`
- **Fix:** `"0\r"` must fail `test_R2_F2_message_content_stores_canonical_stripped_value` until `MessageContent` normalizes on construction, then remain as regression.

## Classified (not triaged)

- **Raw buffer length ≤ cap when valid** — property too strong. Plan caps *stripped* length (`>200` / `>4000` after strip), not raw buffer size. Counterexample: 200 content chars padded to 204 with spaces is valid by spec.
- **`CaptureSession.start()` / `Message.record()` UTC** — already covered by landed triage `R1-F1` / `R1-F2` with proof tests at `6ec2483`; no new edge.

## Retractions

None.
