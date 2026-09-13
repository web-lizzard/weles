---
change_id: db-adapter-capture
title: Capture persists in Postgres and commits atomically with its envelopes
status: implementing
created: 2026-09-13
updated: 2026-09-13T21:10:00Z
archived_at: null
effort_id: db-adapter
slice_ref: S-03
---

## Notes

Embedding construction failures (`EmptyEmbeddingModelError`, `EmbeddingComponentOutOfRangeError`)
are adapter or store invariants, not client input. They stay `CoreException` so the HTTP
exhaustiveness map has a row; the status is 500 (same pattern as `draft_topic_missing`).

Handling them in the application command — a turn failure as an internal fault, not a leaked
value-object error — is out of this slice. `empty_embedding` and `zero_magnitude_embedding`
still map to 422 from capture-flow-draft-note and belong with that same follow-up.
