# Note Detail — Plan Brief

> Full plan: `plan.md`

## What & Why

Slice S-04 of `distill-flow`: users can open a note from the list and read its full content inside Weles (FR-011 / AC-11). Closes the last gap in the read path the domain shape ADR left open — a note can be listed but not opened.

## Starting Point

`GET /notes` and `NoteListOverlay` already exist (S-03, done). No single-note detail route or screen exists yet; `NoteListOverlay` has no row selection.

## Desired End State

Arrow keys move a blue-highlighted selection in the note list; Enter on a `ready` note opens a screen showing its topic, tags, and full content; ESC returns to the list, ESC again returns to capture with its state untouched.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Cards on this screen | Excluded entirely — split into new slice S-06 (`distill-flow-note-cards`) | Cards can be numerous; a scrollable list + expand view is a separate, richer screen that deserves its own change | Session |
| Generating/failed notes | Enter is a no-op until `ready` | Simpler than partial rendering; the list badge already shows progress | Session |
| Note-detail DTO shape | Flat `NoteDetailDTO`, no `cards` field | The endpoint should not touch `CardRepository` at all now that cards live in S-06 | Session |
| Not-found race (note deleted mid-navigation) | Close detail, show the error on the list's existing error banner | Reuses an affordance that already exists rather than building new error UI | Session |
| List cursor + detail-open state | Live on `useAppStore`, not a new store | Matches the existing separation: `useAppStore` = UI-shell nav state, `useNotesStore`/`useNoteDetailStore` = domain data | Research |

## Scope

**In scope:** `GetNote` query + `GET /notes/{note_id}` (note fields only); TUI arrow-key list selection with blue highlight; `NoteDetailScreen` (topic/tags/content); two-level ESC (detail → list → capture).

**Out of scope:** Any card data or UI (→ `distill-flow-note-cards`, S-06); card-to-anchor jump (S-05); the "cards ready" notification (FR-014); scrolling for long content; note editing.

## Architecture / Approach

Backend-first vertical slice, each TDD'able unit as a stubs-then-behavior phase pair: domain exception + DTO + port → adapter behavior → route stub → route behavior → TUI client → TUI stores → `NoteDetailScreen` → (single phase) wiring arrow/Enter/ESC into the two already-tested shell files.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1-2 | `GetNoteQueryPort` + in-memory adapter (note-only, no cards) | Auto-derived exception `code` must not collide with capture's `note_not_found` (verified: it doesn't) |
| 3-4 | `GET /notes/{note_id}`, 200 + 404 | Manual `pnpm generate:api` regen must run before Phase 6 can use the typed path |
| 5-6 | TUI `getNote()` client | Distinguishing the 404 message from other failures |
| 7-8 | `useNoteDetailStore` + `useAppStore` nav fields | Failure path must close detail *and* surface the error on the list, not build new UI |
| 9-10 | `NoteDetailScreen` | None significant — single content view, no tabs |
| 11 | Arrow/Enter/ESC wiring into `NoteListOverlay` + `app.tsx` | Selection must clamp when a poll shrinks the list mid-navigation |

**Prerequisites:** S-01, S-02 (done).
**Estimated effort:** 11 phases, ~1 backend-day + ~1.5 TUI-days.

## Open Risks & Assumptions

- Assumes `pnpm generate:api` is run manually between Phase 4 and Phase 6, as it was for S-03 — no CI step regenerates the schema automatically.
- Assumes reusing the list's error banner for a detail-fetch failure is acceptable UX; if a dedicated detail-error surface is wanted later, it's a small addition to `NoteDetailScreen`, not a redesign.

## Success Criteria (Summary)

- `GET /notes/{note_id}` returns 200 with note-only fields for a known id, 404 with `distill_note_not_found` for an unknown one.
- Arrow keys + Enter open a `ready` note's content in the TUI; ESC pops one level at a time; capture state is untouched across the whole cycle.
