# Restore In-Memory Draft Context on Redraft — Implementation Plan

## Overview

A capture session in `DRAFTING` phase stays there across turns (redraft is not a
re-transition — `CaptureMachine`'s only guarded move out of `DRAFTING` is back to
`CONVERSING` on `conversation_requested`). Every `POST /messages` builds a fresh
`CaptureTurn` in `GenerateReplyCommand.handle`, and `CaptureTurn.draft` always starts
`None`. On a redraft, the session and note already carry the settled topic and tags, but
the turn's in-memory `draft` does not — so if the model calls `propose_note_content` (or
`propose_note_tag`) before re-proposing the topic, `_append_note_content` /
`_resolve_note_tag` raise `DraftTopicMissingError` even though nothing is actually
missing.

This plan restores `context.draft` from what is already persisted, the same way the
session and the note are already loaded into the turn — no ad-hoc hydration in the
command, and no new persisted field.

## Current State Analysis

- `GenerateReplyCommand.handle` (`backend/src/application/capture/commands/send_message.py:73-99`)
  already loads `session` and `note` (when `session.note_id` is set) before constructing
  `CaptureTurn(session=session, messages=prior, note=note)`. `note` is therefore already
  in `context.note` from turn start — nothing to change there.
- `context.draft` is never derived from `context.note`. It is only ever populated inside
  `Drafting`'s actions (`_resolve_note_topic`, `_resolve_note_tag`, `_append_note_content`
  in `backend/src/domain/capture/graph.py:392-426`), each of which requires a prior
  `NoteTopicProposed` in the *same* turn to have set `context.draft` first.
- `NoteVocabularyRepository.resolve(note)` (`backend/src/domain/capture/ports.py:85-86`,
  implemented at `backend/src/adapters/out/in_memory/capture/note_vocabulary_repository.py:20-33`)
  already reconstructs the full `Topic` + `list[Tag]` for a persisted note — it is the
  exact lookup `_reconcile_note_tags` (`graph.py:429-446`) uses at materialisation time.
  `Note` itself already carries `content: NoteContent` (`backend/src/domain/capture/note.py:26`).
  Between the two, everything `NoteDraft` needs is already durable — no new field on
  `Note` is required.
- Every drafting turn ends by applying `DraftCompleted`, which runs `_materialise_note`
  unconditionally when the phase is `DRAFTING` (`send_message.py:204-205`,
  `graph.py:449-472`) — so by the time a second turn starts, whatever the first turn
  drafted is already saved onto `Note` via `topic_id` / `tag_ids` / `content`.
- All existing redraft tests (`tests/unit/capture/test_send_message_command.py`,
  e.g. `test_redraft_turn_updates_topic_tags_and_content_keeping_same_note_id`) script the
  agent to re-propose the topic on every redraft turn, which is why the bug is latent
  today — no existing test scripts a redraft that opens with content or a tag only.

### Key Discoveries:

- `Drafting.get_actions` (`graph.py:181-198`) already branches on event type per turn —
  this is the existing extension point for a hydration action, exactly where
  `change.md`'s Notes point ("an action on `UserMessageRecorded` in state `Drafting`").
  `machine.apply(UserMessageRecorded(...))` runs at the very start of `handle`
  (`send_message.py:99`), before phase dispatch — so this action fires on turn 1 of a
  redraft, before any tool event.
- `_message_recording_actions` (`graph.py:362-369`) is shared between `Conversing` and
  `Drafting` and stays untouched — the new action is `Drafting`-only, since hydrating a
  draft has no meaning in `Conversing`.

## Desired End State

A second (or later) `POST /messages` while a session sits in `DRAFTING` with an existing
note never raises `DraftTopicMissingError` solely because the model called
`propose_note_content` or `propose_note_tag` before `propose_note_topic` — the turn's
`context.draft` already reflects what the persisted note holds, from before any tool event
of that turn runs.

Verify: `test_redraft_content_without_reproposing_topic_keeps_prior_draft_context` (added
in Phase 2) passes; the full backend suite passes; a redraft that *does* re-propose a new
topic still behaves exactly as today (topic/tags/content fully replaced, per the existing
tests).

## What We're NOT Doing

- No new persisted field on `Note` (or elsewhere) to snapshot the draft — `Note`'s
  existing `topic_id` / `tag_ids` / `content` plus `NoteVocabularyRepository.resolve`
  already carry everything `NoteDraft` needs.
- No change to `_resolve_note_topic`'s behaviour when a *new* topic is proposed
  mid-redraft — it already replaces `context.draft` wholesale, which is correct: a new
  topic invalidates the previous tag vocabulary, and `_materialise_note` /
  `_reconcile_note_tags` already reconcile that against the persisted note. This plan
  does not touch `_reconcile_note_tags` or `_materialise_note`.
- No degrade-to-empty-draft fallback when `NoteVocabularyRepository.resolve` raises
  `NoteVocabularyIncompleteError` — it propagates unchanged, exactly as it already does
  from `_reconcile_note_tags` today.
- No SQL adapter work — `capture` has no SQL adapter yet (in-memory only), so nothing
  outside `adapters/out/in_memory/capture/` is touched by this plan.
- No change to `CaptureAgentPort`, the LLM adapter, or the deterministic double — this is
  entirely a domain-graph + application-wiring fix.

## Implementation Approach

Add one new `Drafting`-only action, `_hydrate_draft_from_note`, wired into
`Drafting.get_actions` for `UserMessageRecorded`. It no-ops when `context.draft` is
already set (nothing to hydrate) or `context.note` is `None` (no note drafted yet —
today's first-draft behaviour is untouched). Otherwise it calls
`deps.note_vocabulary.resolve(context.note)` and builds `NoteDraft` from the result plus
`context.note.content`, marking every resolved topic/tag as reused (`topic_reused=True`,
`tag_reused=[True, ...]`) since they already existed in the persisted note before this
turn began.

Split as a stubs-then-behavior pair per the plan skill's TDD pairing (no
`discover-contracts.md` on this change, so the pairing is preserved): Phase 1 declares the
action's signature and wires it in unimplemented; Phase 2 implements it and adds the
regression tests.

## Phase 1: Stubs — declare the hydration action

### Overview

Materialise `_hydrate_draft_from_note`'s signature and its wiring into
`Drafting.get_actions`, unimplemented, so Phase 2's tests can import and exercise the
wiring immediately.

### Changes Required:

#### 1. Domain graph — action stub and wiring

**File**: `backend/src/domain/capture/graph.py`

**Intent**: Introduce the action symbol `_hydrate_draft_from_note` and make it reachable
from `Drafting.get_actions` on `UserMessageRecorded`, without behavior yet.

**Contract**:

```python
async def _hydrate_draft_from_note(
    context: CaptureTurn, deps: CaptureDeps, event: CaptureEvent
) -> None:
    raise NotImplementedError
```

Wired into `Drafting.get_actions` (`graph.py:181-198`) alongside the existing
`selected.extend(_message_recording_actions(event))` line:

```python
if isinstance(event, UserMessageRecorded):
    selected.append(_hydrate_draft_from_note)
```

### Success Criteria:

#### Automated Verification:
- `uv run mypy src/domain/capture/graph.py` (or the project's equivalent type-check
  command) passes with the new symbol in place.
- Existing `tests/unit/capture/test_capture_graph.py` and
  `tests/unit/capture/test_send_message_command.py` still pass unmodified (the stub is
  never invoked with real behavior yet — `NotImplementedError` would only fire once
  Phase 2's tests call it, which don't exist yet).

---

## Phase 2: Behavior — rebuild the draft from the persisted note

### Overview

Implement `_hydrate_draft_from_note` and add the tests that prove the redraft bug is
fixed, at both the domain-graph level and the command level.

### Changes Required:

#### 1. Domain graph — hydration behavior

**File**: `backend/src/domain/capture/graph.py`

**Intent**: Rebuild `context.draft` from the persisted note when a redraft turn starts
without one, using the same vocabulary-resolution the materialisation path already
trusts.

**Contract**:

```python
async def _hydrate_draft_from_note(
    context: CaptureTurn, deps: CaptureDeps, event: CaptureEvent
) -> None:
    _ = event
    if context.draft is not None or context.note is None:
        return
    vocabulary = await deps.note_vocabulary.resolve(context.note)
    context.draft = NoteDraft(
        topic=vocabulary.topic,
        topic_reused=True,
        tags=vocabulary.tags,
        tag_reused=[True] * len(vocabulary.tags),
        content=context.note.content.value,
    )
```

`NoteVocabularyIncompleteError` (raised by `resolve` when a topic or tag has gone
missing) propagates unchanged — no `try`/`except` added.

### Success Criteria:

#### Automated Verification:
- `tests/unit/capture/test_capture_graph.py`: a new test constructs a `CaptureTurn` with
  `phase=CapturePhase.DRAFTING`, a persisted `note` whose `topic_id`/`tag_ids`/`content`
  are pre-seeded via the in-memory topic/tag/note-vocabulary repositories, and
  `draft=None`; applying `UserMessageRecorded` populates `context.draft` with the
  resolved topic, tags (`tag_reused` all `True`), and the note's existing content. A
  second test asserts the action no-ops when `context.draft` is already set, and a third
  when `context.note` is `None`.
- `tests/unit/capture/test_send_message_command.py`: a new test,
  `test_redraft_content_without_reproposing_topic_keeps_prior_draft_context`, scripts a
  `_ScriptedCaptureAgent` turn sequence where the first turn proposes topic + tag +
  content (as today's helpers do), and the **second** turn's script omits
  `NoteTopicProposed` entirely — `[ReplyProduced(...), NoteContentProduced(...)]` — and
  asserts the second turn completes with a `DraftDoneEvent` (same `note_id`, appended
  content) instead of raising `DraftTopicMissingError`.
- Full existing redraft suite in `test_send_message_command.py` (including
  `test_redraft_turn_updates_topic_tags_and_content_keeping_same_note_id`,
  `test_redraft_removes_dropped_tags_from_persisted_note_R2_F4`,
  `test_redraft_adds_new_tags_to_persisted_note_R2_F5`) continues to pass unmodified —
  proving a redraft that *does* re-propose a topic still fully replaces
  topic/tags/content as before.
- Full backend test suite passes.

#### Manual Verification:
- Run the full backend suite (`uv run pytest`) once after the rename/implementation, per
  the same discipline the sibling change `llm-adapter-instruction-context` used at its
  phase 5 (`5.7 Run the full backend suite after the rename`).

---

## Testing Strategy

### Unit Tests:
- `tests/unit/capture/test_capture_graph.py` — `_hydrate_draft_from_note` in isolation,
  no agent, no HTTP: hydrates from a persisted note, no-ops on an already-set draft, and
  no-ops with no note.

### Integration Tests:
- `tests/unit/capture/test_send_message_command.py` — the exact bug repro from
  `change.md`'s Notes: second `POST /messages` in `DRAFTING`, model proposes content
  before topic.

### Manual Testing Steps:
- Full backend suite run after Phase 2.

## References

- `context/changes/capture-redraft-draft-context/change.md` — the debugging notes that
  diagnosed the bug and named the fix's rightful location.
- `context/changes/llm-adapter-instruction-context/` — the change this one's `origin`
  points at; establishes `CaptureMachine`'s instruction/action wiring conventions this
  plan follows.
