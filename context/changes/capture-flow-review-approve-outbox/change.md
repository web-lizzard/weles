---
change_id: capture-flow-review-approve-outbox
title: Users can reshape and approve the draft before it reaches the outbox
status: implementing
created: 2026-09-02
updated: 2026-09-02T17:08:02Z
archived_at: null
origin: overview-thougts
effort_id: capture-flow
slice_ref: S-06
---

## Context

- Origin (duck `overview-thougts`): [`context/duck-sessions/overview-thougts/log.md`](../../duck-sessions/overview-thougts/log.md) — capture path, outbox, approval policy.
- Outbox shape (duck `outbox-shared`): [`context/duck-sessions/outbox-shared/log.md`](../../duck-sessions/outbox-shared/log.md) — settled envelope shape, UnitOfWork-member atomicity, and the `note_approved` payload this slice's push needs.

## Notes

<!-- Materialized from effort `capture-flow`, slice S-06. Run /plan capture-flow-review-approve-outbox to write the plan. -->
