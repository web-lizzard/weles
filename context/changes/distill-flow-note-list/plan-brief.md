# Note List — Plan Brief

> Full plan: `plan.md`

## What & Why

Slice S-03 of `distill-flow`: users need to see their notes (topic, distillation state, live card count) without losing an in-flight capture session. The domain shape ADR deliberately left the read path undecided — this plan adds it: a backend `ListNotes` query + `GET /notes`, and a TUI overlay reachable via `/notes`.

## Starting Point

Backend has `Note`/`Card` aggregates and repositories but no query layer for distill and no HTTP read route. TUI renders only `CaptureScreen`, with a single-command (`/approve`) exact-match dispatcher and one populated Zustand store (`chat.ts`) plus one empty one (`index.ts`'s `useAppStore`).

## Desired End State

`GET /notes` returns every note, most-recent-first, each with topic/status/card-count. In the TUI, `/notes` opens `NoteListOverlay` over the still-mounted `CaptureScreen`; ESC closes it; the overlay polls so status transitions appear live; no capture-session field ever changes value across an open/close cycle.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Recency field ownership | `Note.updated_at`, bumped only by `Note`'s own methods via a private `_touch` | Nothing outside the aggregate should ever mutate it — domain owns its own field completely | Plan session |
| Card-activity recency | Computed at read time as `max(note.updated_at, max(live card.created_at))`, no cross-aggregate write | Preserves domain purity while still handling a future card-write path not tied to a note transition | Plan session |
| Stuck-in-`GENERATING` display | Badge + elapsed age, no sweeper/retry | Gives a visible signal without building timeout logic the ADR left undecided | Plan session |
| TUI notes state | Dedicated `useNotesStore`, separate from `chat.ts`; poll lifecycle in a `useNotesPolling` hook tied to the overlay's own mount/unmount | Clean isolation; no separate open/close-orchestration layer needed since mount already tracks open state | Plan session |
| Close gesture | ESC closes, `/notes` opens | Symmetric, first `useInput` use in this codebase | Plan session |
| Fetch-error display | Inline message, list stays visible, auto-retry on next poll tick | No extra retry-button UI; polling already re-tries every interval | Plan session |
| Polling test approach | `vi.useFakeTimers()` + mocked `notes.ts`, not a new mock-service library | Matches the existing `vi.stubGlobal("fetch", ...)` convention in `stream.test.ts` | Plan session |
| `GET /notes` scale | No pagination — return the full list | MVP scale, single user, in-memory store | Plan session |

## Scope

**In scope:** `Note.updated_at`; `ListNotesQueryPort` + in-memory adapter; `GET /notes` + OpenAPI regen; TUI notes API client, store, polling hook, overlay shell/dispatch/ESC, `NoteListOverlay` component.

**Out of scope:** note detail (S-04), card-to-anchor jump (S-05), the "cards ready" notification (FR-014), pagination, any Card model change, a stuck-generating sweeper, any SQL/durable adapter.

## Architecture / Approach

Backend-first vertical slice, CQRS-lite (query reads straight into DTOs, no `UnitOfWork`). Each TDD'able unit is a stub-then-behavior phase pair: domain recency → read model → HTTP route, then TUI client → store/polling → overlay shell/dispatch → presentational component.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1-2 | `Note.updated_at`, domain-owned | None — small, self-contained |
| 3-4 | `ListNotesQueryPort` + in-memory read logic | Getting the recency `max()` and three-way status mapping right |
| 5-6 | `GET /notes` + OpenAPI regen | None — mirrors `/_outbox` exactly |
| 7-8 | TUI notes API client | None — mirrors existing `stream.ts` calls |
| 9-10 | `useNotesStore` + polling | Fake-timer test correctness for interval start/stop |
| 11-12 | Overlay shell, `/notes` dispatch, ESC | First `useInput` use in this codebase; must not unmount `CaptureScreen` |
| 13-14 | `NoteListOverlay` rendering | Badge/age mapping correctness for the three FR-010 cases |

**Prerequisites:** S-01, S-02 (done — notes and cards already exist and generate automatically).
**Estimated effort:** 14 phases, cross-cutting backend + TUI.

## Open Risks & Assumptions

- Assumes `Card.created_at` is timezone-consistent with `Note.updated_at` (both `datetime.now(UTC)`-derived) — not independently re-verified beyond existing code inspection.
- Poll interval fixed at 3000ms; not user-configurable, no upstream requirement for one.

## Success Criteria (Summary)

- `GET /notes` returns correctly ordered, correctly-statused, correctly-counted notes.
- `/notes` opens a live-updating overlay in the TUI; ESC closes it; capture-session state is provably unchanged across the cycle.
