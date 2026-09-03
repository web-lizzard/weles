# Mutation test — phases 2, 4, 8

ran at 1266137

| Field | Value |
| --- | --- |
| change-id | capture-flow-review-approve-outbox |
| scope | phases 2, 4, 8 |
| engine | mutmut 3.7.0 + pytest (`context/foundation/test-stack.md`) |
| date | 2026-09-03 |

## Mutate surface

| File | Phase |
| --- | --- |
| `backend/src/domain/shared/outbox/model.py` | 2 |
| `backend/src/domain/capture/outbox.py` | 2 |
| `backend/src/adapters/http/errors.py` | 2 |
| `backend/src/adapters/out/in_memory/shared/outbox/appender.py` | 4 |
| `backend/src/adapters/out/in_memory/shared/outbox/store.py` | 4 |
| `backend/src/adapters/out/in_memory/shared/outbox/claimer.py` | 4 |
| `backend/src/application/capture/commands/send_message.py` | 8 |
| `backend/src/application/capture/commands/approve_note.py` | 8 |

291 mutants exercised; 14 survived; 277 killed.

## Specimens

### R2-F1 — claim must stamp UTC on claimed_at

- **Severity**: WARNING
- **Operator**: `argument_replacement`
- **Location**: `backend/src/domain/shared/outbox/model.py:68`
- **Tests still passed**: Survived
- **Mutant**: `datetime.now(UTC)` → `datetime.now(None)`
- **Fix:** assert `claim()` sets `claimed_at.tzinfo is UTC`

### R2-F2 — outbox snapshot/restore must deep-copy envelopes

- **Severity**: WARNING
- **Operator**: `copy_replacement`
- **Location**: `backend/src/adapters/out/in_memory/shared/outbox/store.py:14`
- **Tests still passed**: Survived
- **Mutant**: `copy.deepcopy(...)` → `copy.copy(...)` in `snapshot()` and `restore()`
- **Fix:** assert mutating an envelope after `snapshot()` does not alter the restored store state

### R2-F3 — claimer must forward worker_id to envelope.claim

- **Severity**: WARNING
- **Operator**: `argument_replacement`
- **Location**: `backend/src/adapters/out/in_memory/shared/outbox/claimer.py:10`
- **Tests still passed**: Survived
- **Mutant**: `envelope.claim(worker_id)` → `envelope.claim(None)`
- **Fix:** assert every envelope returned from `InMemoryOutboxClaimer.claim(..., worker_id="w1")` has `claimed_by == "w1"`

### R2-F4 — redraft must remove dropped tags from the persisted note

- **Severity**: CRITICAL
- **Operator**: `comparison_negation`
- **Location**: `backend/src/application/capture/commands/send_message.py:190`
- **Tests still passed**: Survived
- **Mutant**: `if tag.id not in resolved_ids` → `if tag.id in resolved_ids`
- **Fix:** assert a redraft turn whose resolved tag set drops a prior tag leaves `note.tag_ids` matching only the new labels (not merely `DraftDoneEvent.tags`)
- **proof-test skipped**: HEAD on default branch — test written at `tests/unit/capture/test_send_message_command.py::test_redraft_removes_dropped_tags_from_persisted_note_R2_F4`, green against production code

### R2-F5 — redraft must add new tags to the persisted note

- **Severity**: CRITICAL
- **Operator**: `comparison_negation`
- **Location**: `backend/src/application/capture/commands/send_message.py:194`
- **Tests still passed**: Survived
- **Mutant**: `if tag.id not in current_ids` → `if tag.id in current_ids`
- **Fix:** assert a redraft turn that introduces a tag absent from the note persists that tag on `note.tag_ids`
- **proof-test skipped**: HEAD on default branch — test written at `tests/unit/capture/test_send_message_command.py::test_redraft_adds_new_tags_to_persisted_note_R2_F5`, green against production code

### R2-F6 — draft content must accumulate across multiple DraftContentChunks

- **Severity**: WARNING
- **Operator**: `assignment_replacement`
- **Location**: `backend/src/application/capture/commands/send_message.py:130`
- **Tests still passed**: Survived
- **Mutant**: `draft_text += chunk.text` → `draft_text = chunk.text`
- **Fix:** assert a turn with two `DraftContentChunk` values persists concatenated content on the note and in `DraftDoneEvent`

## Classified (not triaged)

| Operator | Location | Why classified |
| --- | --- | --- |
| `assignment_replacement` | `send_message.py:93` (`full_text = "XXXX"`) | Every exercised draft path also emits `ReplyTextChunk`; initial `full_text` is overwritten before persistence. |
| `assignment_replacement` | `send_message.py:95` (`saw_draft = None` at init) | `if saw_draft:` treats `None` and `False` identically at the guard site. |
| `annotation_replacement` | `send_message.py:96` (`resolved_topic: Topic \| None = ""`) | Runtime annotation default; no behavioural change under CPython 3.12. |
| `assignment_replacement` | `send_message.py:105,115` (`saw_draft = None` on topic/tag chunk) | Later draft chunks in every test scenario reset `saw_draft` to a truthy value before the post-stream guard. |
| `assignment_replacement` | `send_message.py:105,115` (`saw_draft = False` on topic/tag chunk) | Same — subsequent `DraftContentChunk` branch sets `saw_draft = True`. |
