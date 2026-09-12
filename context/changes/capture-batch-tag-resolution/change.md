---
change_id: capture-batch-tag-resolution
title: Batch tag vocabulary resolution with one embedding call per tag run
status: new
created: 2026-09-12
updated: 2026-09-12
archived_at: null
origin: llm-adapter-capture-modes
---

## Notes

Follow-up to `llm-adapter-capture-modes` (phase 17). Deferred on purpose so the capture-modes
change can close without widening scope.

### Problem

After phase 17, each `NoteTagProposed` from the capture agent triggers `machine.apply` →
`_resolve_note_tag` → `VocabularyResolver.resolve_tag` → one `EmbeddingPort.embed` call. Adapters
often emit several tag labels in a row (e.g. deterministic in-memory drafting loop), so embedding
and candidate matching run **sequentially** with **N provider round-trips**. Parallel
`asyncio.gather` on `resolve_tag` would still be N API calls; the goal is **one batch embed** per
consecutive tag run.

### Desired behaviour

- Adapter surface can stay as today: multiple `NoteTagProposed` events (or multiple
  `propose_note_tag` tool returns).
- The **command** coalesces a **consecutive run** of tag events before `apply`.
- The **domain** resolves the whole run in one action with one `resolve_tags` call: fetch tag
  candidates once, `embed_many` once, then match labels **in order** (duplicate labels in one batch
  must reuse minted tags within the batch — same invariant as
  `test_resolve_tag_reuses_a_tag_minted_earlier_in_the_same_stream`).
- **SSE** unchanged for clients: still one `DraftTagEvent` per label in order; only the timing
  shifts to flush after the batch (on first non-tag event or end of drafting stream).

### Contract sketch (to refine in `/plan`)

| Layer | Change |
| --- | --- |
| `EmbeddingPort` | Add `embed_many(texts: Sequence[str]) -> Sequence[Embedding]`; keep `embed` as single-text wrapper or delegate to `embed_many`. |
| `VocabularyResolver` | Add `resolve_tags(labels, tags: TagRepository) -> Sequence[ResolvedTag]`. |
| `CaptureEvent` | Introduce `NoteTagsProposed(labels: tuple[Label, ...])`; routing replaces per-label `_resolve_note_tag` with `_resolve_note_tags`. |
| `AgentEvent` | Either keep `NoteTagProposed` and normalize in the command, or add plural at adapter boundary later. |
| `GenerateReplyCommand` | Buffer consecutive `NoteTagProposed`; flush to `NoteTagsProposed` before other events; map flushed batch to multiple `DraftTagEvent` from `context.draft`. |

Topic resolution stays single-label (`resolve_topic` / `NoteTopicProposed`) unless a similar batch
need appears later.

### Non-goals (for now)

- Changing HTTP DTO shapes or client contracts.
- Replacing multiple LLM tool calls with one `propose_note_tags` tool (optional follow-up).
- Langfuse span grouping beyond what a single `embed_many` observation implies.

### Open decisions for planning

1. Whether `NoteTagProposed` remains in `AgentEvent` forever with command-side coalescing only.
2. Contract-test cadence for `embed_many` on OpenRouter vs in-memory only in CI.
3. Whether redraft turns with interleaved tag/content ordering need extra ordering tests beyond
   current capture graph coverage.
