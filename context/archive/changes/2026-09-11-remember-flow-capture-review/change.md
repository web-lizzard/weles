---
change_id: remember-flow-capture-review
title: Users can open a review from within a capture session and return to the conversation with nothing lost
status: archived
created: 2026-09-11
updated: 2026-09-11
archived_at: 2026-09-11T16:09:42Z
origin: remember-pillar
effort_id: remember-flow
slice_ref: S-06
---

## Notes

<!-- Materialized from effort `remember-flow`, slice S-06 (combines former S-06 capture entry and S-07 capture prompt). -->

Narrowed 2026-09-11 to AC-21 and AC-22. AC-16 was dropped with FR-012 — see `context/efforts/remember-flow/prd.md` v2 Non-Goals: a prompt at the close of capture only carries value if it holds the user synchronously and waits for an answer; without that wait it is the same information the always-visible due count already shows.

Both remaining criteria are already satisfied by code shipped under S-01 (`remember-flow-review-session-tui`, commit 6041d50):

- AC-21 — `SittingOverlay` renders as an absolute overlay above a never-unmounted `CaptureScreen` (`tui/src/app.tsx`); ESC resets only `useSittingStore`, leaving `useChatStore` untouched. Covered by `tui/test/app.test.tsx` ("closes the sitting overlay on ESC…", "blocks capture input while the sitting overlay is open").
- AC-22 — `handleSubmit` matches `/remember` by exact equality, so every other input goes to `sendUserMessage` (`tui/src/screens/CaptureScreen.tsx`). Partially covered: `app.test.tsx` asserts `sendMessage` is not called for `/remember`, but the inverse — prose mentioning "remember" staying in the conversation — has no test, unlike the `/approve` analogue in `captureScreen.test.tsx`.

Remaining work is therefore one test, not a feature. Run `/plan remember-flow-capture-review` only if that test warrants a plan; otherwise close the slice on the missing-test addition.
