---
change_id: remember-flow-review-session-tui
title: Remember flow review session TUI
status: archived
created: 2026-09-10
updated: 2026-09-10
archived_at: 2026-09-10T14:49:21Z
origin: remember-flow-review-session
---

## Notes

Phase 2 scope includes `tui/src/api/client.ts`: `delegatedFetch` unwraps openapi-fetch
`Request` instances so Vitest's global `fetch` stubs receive plain `(url, init)` calls.
Direct coverage lives in `tui/test/client.test.ts` (R2-F1 / R2-F2).
