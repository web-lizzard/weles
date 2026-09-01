# Drafted Note and Topic — Plan Brief

> Full plan: `plan.md`

## What & Why

When the user signals in conversation that they are done, the agent stops probing and instead drafts a note — topic, tags, body — synthesized from the transcript, streamed into the TUI as it is produced and persisted as a `Note`. This is slice S-04 of `capture-flow`, realizing AC-08 and AC-09: the user never writes the note themselves, and the drafted topic may be more specific than the one they named at the start.

## Starting Point

The conversation half already runs end to end: sessions open over HTTP, agent replies stream over SSE, and the Ink TUI renders transcript, topic and coverage banner. `Note`, `Tag` and the note-level `Topic` aggregate do not exist; `ReplyGenerationPort` yields bare strings, so a stream cannot say what kind of content a chunk carries.

## Desired End State

The user types something that reads as "we're done". In the same turn, with no new command or endpoint, the agent replies with a short hand-off line and the TUI's draft panel fills in: topic heading first, then tags one by one, then the body streaming in. A `Note` in status `draft` is persisted, pointing at a freshly minted `Topic` and `Tag` rows that each carry an embedding, with `CaptureSession.note_id` naming it.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Vocabulary scope | Always mint, plus a new `EmbeddingPort`; no similarity search | Keeps AC-10/AC-11 in S-05 while giving the aggregates their ADR shape from day one, so S-05 has no embeddings to backfill | Plan |
| `CaptureSession.start()` | Unchanged; only `draft_note()` is added | AC-08/AC-09 do not need the ADR's `start(topic)`, and changing it would rewrite two archived slices and the session-start UX | Plan |
| Port contract | `ReplyGenerationPort.generate() -> AsyncIterator[ReplyChunk]` | A tool-calling model decides mid-turn what it is producing, so the stream itself has to carry that distinction | Plan |
| Chunk type | Discriminated union on `kind`, not a flat record | `topic`/`tag` carry whole validated `Label`s while `reply`/`note` carry raw fragments — a real difference in payload shape | Plan |
| Draft trigger | The model, inside an ordinary turn | FR-005 makes the user's explicit confirmation the trigger, and that confirmation is a conversational act, not a UI mode | Frame |
| Chunk order | `reply`+ → `topic` → `tag`* → `note`* | Fixing the order in the port contract removes the need for a separate "tags complete" signal | Plan |
| Naming | Value object → `SessionTopic`; aggregate takes `Topic` | The ADR's name belongs on the object the ADR describes | Plan |
| One note per session | `note_id` on `CaptureSession`, guarded in `draft_note()` | Makes the PRD's non-goal an assertion on a pure object; reshape in S-06 goes through `Note`'s mutators, not back through `draft_note()` | Plan |
| Mid-stream failure | Roll the whole turn back | Matches how the conversation path already uses one `UnitOfWork` per turn, and gives AC-07's "no trace" for free | Plan |
| `draft_done` payload | Carries the full persisted note | The client's accumulated fragments and what was stored can differ, and the stored value wins — same reason `done` already carries the full reply | Plan |

## Scope

**In scope:** `Note`, `Topic` and `Tag` aggregates with their repository ports; `SessionTopic` rename; `note_id` and `draft_note()` on `CaptureSession`; the `ReplyChunk` union and the retyped generation port; `EmbeddingPort` and a deterministic adapter; three in-memory repositories inside the extended `UnitOfWork`; `VocabularyResolver`; chunk routing in `GenerateReplyCommand`; four new SSE events; AC-08/AC-09 acceptance scenarios; TUI parser, store slice and draft panel.

**Out of scope:** reuse-or-mint and similarity search (S-05); `Note` mutators, `approve()`, `close()`, the outbox envelope (S-06); a real LLM adapter with tool calls; aligning `start()` to the ADR's `start(topic)`; any query path that reads notes back.

## Architecture / Approach

The trigger is conversational, so it reaches the application as a property of the stream rather than as a separate call. `ReplyGenerationPort` is retyped to yield a discriminated union whose `kind` says whether a chunk is reply text, a topic label, a tag label, or note body text; ordering is part of the port's contract and is enforced by its contract test. `GenerateReplyCommand` routes chunks: reply text becomes the agent `Message`; a topic or tag label goes through `VocabularyResolver`, which embeds, mints and persists it, and only the resolved label goes out as an SSE event; note text accumulates into `NoteContent`. At end of stream the command calls `session.draft_note(...)`, saves, commits, then yields `draft_done` followed by `done`. One `UnitOfWork` per turn throughout.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Rename `Topic` → `SessionTopic` | Frees the ADR's name for the aggregate | A missed reference, or a wire-code change slipping past the exception table |
| 2. Domain vocabulary and aggregates — stubs | Every domain symbol phase 3 imports | — |
| 3. Domain vocabulary and aggregates — behavior | Validators, factories, both `draft_note()` guards | The closed-session guard is unreachable via HTTP until S-06 |
| 4. Chunk protocol and SSE events — stubs | `ReplyChunk` union, four events, `EmbeddingPort`, extended `UnitOfWork` | The port retype breaks its only adapter and only consumer at once |
| 5. Deterministic draft adapter — behavior | Confirmation-phrase mode switch; ordering pinned in the contract test | The phrase list is a stand-in that a real model will not reproduce |
| 6. In-memory persistence and UoW — stubs | Three repositories, embedding adapter, both composition roots | — |
| 7. In-memory persistence and UoW — behavior | Four contract suites plus the five-store rollback test | A new store left outside the snapshot set silently voids rollback |
| 8. Resolver and command routing — stubs | `VocabularyResolver`, per-kind dispatch skeleton | — |
| 9. Resolver and command routing — behavior | Drafting end to end in the application layer | The largest phase; event ordering and rollback both live here |
| 10. HTTP integration and AC-08/AC-09 | SSE sequence over the wire, Gherkin scenarios | A step module not registered in `pytest_plugins` never loads |
| 11. TUI data layer — stubs | Client event types and the `draft` store slice | — |
| 12. TUI data layer — behavior | Parser branches and store reducers | Local accumulation must yield to the `draft_done` payload |
| 13. TUI screen — stubs | `DraftNotePanel` placed in the layout | — |
| 14. TUI screen — behavior | The panel renders live; row budget updated | An uncounted fixed block overflows the brand header |

**Prerequisites:** S-02 (`capture-flow-coverage-wrapup`), done and archived.
**Estimated effort:** large — 14 phases across domain, application, adapters and TUI, seven of them TDD'able.

## Open Risks & Assumptions

- `CaptureSession` stays divergent from the ADR's `start(topic: str)`. Recorded as deliberate debt with no owner yet; someone has to reconcile it before the ADR reads as implemented.
- `note_id` on `CaptureSession` is an addition beyond the ADR's listed shape, taken so the one-note invariant is provable without a repository lookup.
- Until S-06 lands reshape, a second confirmation in the same session surfaces an error rather than a redraft. Deliberate: honest over silently producing a second note.
- The confirmation-phrase rule is an in-memory stand-in for a tool call. It makes AC-08 testable through HTTP, but says nothing about how a real model will decide.
- Resolving labels before emitting their events costs one `embed()` round trip of heading latency, accepted so S-05's reuse does not rewrite the heading mid-stream.

## Success Criteria (Summary)

- AC-08 and AC-09 scenarios green: `cd backend && uv run pytest tests/bdd -m "capture-flow and (AC-08 or AC-09)" -v`
- Full suites green: `cd backend && uv run pytest` and `pnpm --dir tui test`
- Running backend and TUI together, a confirmation phrase fills the draft panel with topic, then tags, then body, and the note is persisted.
