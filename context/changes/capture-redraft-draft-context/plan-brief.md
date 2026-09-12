# Restore In-Memory Draft Context on Redraft — Plan Brief

> Full plan: `plan.md`

## What & Why

A capture session stays in `DRAFTING` across redraft turns, but each turn builds a fresh
`CaptureTurn` whose `draft` field always starts `None`. If the model proposes note
content (or a tag) before re-proposing the topic on a redraft, the domain raises
`DraftTopicMissingError` — even though the topic and tags already live on the persisted
note. This plan rebuilds the turn's draft from what is already durable, instead of
requiring the model to re-walk topic → tags → content on every redraft.

## Starting Point

`GenerateReplyCommand` already loads the persisted `Note` into the turn when
`session.note_id` is set. `NoteVocabularyRepository.resolve(note)` already reconstructs
the full `Topic` + `list[Tag]` for that note (used today at materialisation time), and
`Note` already carries its own `content`. Nothing about the draft's substance is
missing from storage — only the in-memory `NoteDraft` view of it.

## Desired End State

A redraft turn that opens with content or a tag — no topic re-proposal — completes
normally, keeping the note's existing topic/tags and appending the new content, exactly
as if the topic had been re-proposed unchanged.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Where the draft's data lives | Derive from existing `Note` fields + `NoteVocabularyRepository`, no new field | Note already carries `topic_id`/`tag_ids`/`content`, and `resolve()` already turns that into full `Topic`/`Tag` objects | Plan (user-confirmed) |
| Where hydration runs | A new `Drafting`-only action on `UserMessageRecorded`, no-op when a draft or note is absent | Redraft never re-transitions into `DRAFTING`, so the transition-guard hook can't catch it — this fires on every turn's first event instead | Plan (change.md diagnosis) |
| Hydration error handling | Propagate `NoteVocabularyIncompleteError` unchanged | Matches how the same error already surfaces from `_reconcile_note_tags` at materialisation time | Plan (user-confirmed) |
| Reused flags on a hydrated draft | `topic_reused=True`, every `tag_reused=True` | Everything hydrated already existed in the persisted note before this turn began | Plan |

## Scope

**In scope:** one new action in `domain/capture/graph.py`, wired into `Drafting.get_actions`; tests in `test_capture_graph.py` and `test_send_message_command.py`.

**Out of scope:** any new persisted field, SQL adapter work (capture has none yet), `CaptureAgentPort`/LLM adapter/deterministic double, `_resolve_note_topic`'s existing replace-on-new-topic behavior.

## Architecture / Approach

`Drafting.get_actions` already branches per event type each turn. The new action slots
in on `UserMessageRecorded` — which fires before any tool event, since
`machine.apply(UserMessageRecorded(...))` runs at the very start of
`GenerateReplyCommand.handle`. It hydrates `context.draft` from `context.note` (already
loaded) via `deps.note_vocabulary.resolve`, only when no draft exists yet.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Stubs | `_hydrate_draft_from_note` signature + wiring, unimplemented | None — no behavior change yet |
| 2. Behavior | Hydration logic + regression tests for the exact bug repro | Existing redraft tests (which always re-propose topic) must keep passing unchanged |

**Prerequisites:** none — builds on already-merged `llm-adapter-instruction-context` work.
**Estimated effort:** small — one new action, two phases, no schema change.

## Open Risks & Assumptions

- Assumes no other caller relies on `context.draft` staying `None` at redraft turn start;
  the existing redraft test suite (which always re-proposes topic) is the check for that.

## Success Criteria (Summary)

- A redraft turn that skips re-proposing the topic no longer raises `DraftTopicMissingError`.
- Every existing redraft test still passes unmodified.
- Full backend suite green.
