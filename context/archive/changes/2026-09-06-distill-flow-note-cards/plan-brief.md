# Note Cards View — Plan Brief

> Full plan: `plan.md`

## What & Why

Slice S-06 delivers AC-12 / FR-012: the cards generated from an open note are visible from that note. It was split out of S-04 so note detail stays scoped to note content; this change owns the card read surface end to end — a new backend query and route, and a two-tab note view in the TUI.

## Starting Point

The domain is complete: the `Card` aggregate and `CardRepository.list_by_note` exist and are wired, but are read only internally to compute `card_count` for the note list. There is no `/cards` route, no card DTO, no card OpenAPI types, and no card screens; `app.tsx` supports a single note-list/note-detail conditional.

## Desired End State

Enter on a `ready` note opens a note view with a `Note` / `Cards` tab strip, the active tab on a blue background in black text. `→` crosses to the cards tab when the note has cards, `←` comes back. Under `Cards`, a scrollable list of live cards; Enter opens one in full with the strip still pinned; `←` returns; `r` refetches. ESC keeps its existing meaning — note view to note list, note list to capture.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Card detail surface | Dedicated card view, tab strip pinned, body swaps | Card sides run to 2000 chars, so one card needs the screen — and keeping the strip preserves context | Plan |
| Entry gesture | `→` from the note tab, `←` back | Tab axis reads naturally on a two-tab view and leaves Enter free for depth | Plan |
| ESC semantics | Unchanged from S-04: pops one level | Keeps the established stack rather than reshaping working navigation | Plan |
| Zero cards | `→` is inert when the note's card count is 0 | Mirrors Enter being inert on non-ready notes in the list | Plan |
| Freshness | Fetch on open plus an `r` refresh key | Cards for a `ready` note are terminal, so polling would re-fetch unchanged data | Plan |
| Route shape | `GET /notes/{note_id}/cards` | Nested under the note matches the selection-addressed navigation intent | Research |
| Card ordering | `created_at` ascending | Generation order is the natural reading order | Plan |
| Card detail data | From the already-fetched list | Avoids a `CardRepository.get` port and a second query for data in hand | Plan |
| Unknown note | `DistillNoteNotFoundError` → 404 | The mapping already exists in `errors.py`; no new handler | Research |

## Scope

**In scope:** `ListCardsForNoteQueryPort` + `CardListItemDTO`; in-memory query adapter with the live-card filter; the nested HTTP route and its composition wiring; OpenAPI regeneration; a TUI cards API module and store; `useAppStore` tab and card-selection state; a tab-strip component; card list and card detail screens; `app.tsx` routing; unit, store, screen and HTTP integration tests.

**Out of scope:** anchor jump (S-05); the cards-ready notification (FR-014); card removal, regeneration or note editing; discarded cards in any user-facing read; a `CardRepository.get` port; polling the cards view; a US-06 BDD feature file; any change to `GetNote` or to S-04's ESC behavior.

## Architecture / Approach

Standard CQRS-lite read path — `Protocol` port plus pydantic DTO in `application/distill/queries/`, an in-memory adapter reading through `CardRepository` with the `discard is None` filter, and a route on the existing notes router. The TUI mirrors the note-detail slice: typed API module, fetch-on-navigate Zustand store, screens reading from both stores. Navigation is a tab axis (`←`/`→`) plus a depth axis (Enter / `←`) inside the already-open note view, with ESC untouched.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Backend card-read contracts | Query port, DTO, adapter shell, route, wiring | Route registered but inert until phase 2 |
| 2. Backend card-read behavior | Live filter, ordering, 404, HTTP integration tests | Missing the `discard is None` filter would surface fabricated cards |
| 3. OpenAPI + TUI card surface stubs | Regenerated `schema.d.ts`, `cards.ts` and store signatures | Regeneration needs a running backend with phase 1 merged |
| 4. TUI card fetch behavior | `listCards` mapping, store fetch/refresh/error paths | Error path must reach the existing notes banner, not a new one |
| 5. TUI navigation and screen stubs | App-store tab/card state, tab strip, two screen shells | New state must default so existing navigation is untouched |
| 6. TUI navigation behavior | `←`/`→`, disabled entry at zero cards, Enter/`←` depth, `r`, routing | `←` is overloaded — card detail must be checked before the tab switch |

Phases 1/2, 3/4 and 5/6 are stubs-then-behavior pairs; the behavior phase of each pair carries the `#### Tests` row.

**Prerequisites:** S-04 (`distill-flow-note-detail`) — done and archived. Phase 3 needs the backend running with phase 1 in place.

**Estimated effort:** ~1–2 days.

## Open Risks & Assumptions

- The gating card count comes from `useNotesStore`, populated by the note-list poll, so it can lag a note that just finished generating; `r` and reopening both recover.
- `←` carries two meanings inside the cards tab; the ordering guard in phase 6 is what keeps them separate.
- Long lists are not virtualized — selection clamps but the list does not scroll-window; acceptable at expected card volumes and revisitable if it bites.

## Success Criteria (Summary)

- `GET /notes/{note_id}/cards` returns only live cards, oldest first, `[]` for a card-less note, 404 for an unknown one.
- From an open `ready` note, `→` reveals its cards, Enter reads one in full, and `←` walks back out; `→` is inert at zero cards.
- Backend `pytest` and TUI `npm test` / `npm run build` all pass, with new coverage for the route, the client, the store and the navigation.
