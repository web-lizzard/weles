---
date: 2026-09-08T01:17:00+02:00
topic: "Domain and TUI requirements synthesis for distill-flow-note-cards"
topic_slug: null
container_id: distill-flow-note-cards
tags: [research, distill, domain, tui, backend]
last_updated: 2026-09-08
---

# Research: Domain and TUI requirements synthesis for distill-flow-note-cards

## Research Question

syntezuj wymaganie - domene i tui dla distill-flow-note-cards

## Summary

Slice S-06 (`distill-flow-note-cards`) delivers AC-12 / FR-012: from an open note, the user can see the cards that note produced. The change was split out of S-04 (`distill-flow-note-detail`) so the note-detail screen stays scoped to note content only; S-06 owns the cards-list/card-detail screen and its own backend read surface.

The **domain layer is largely complete** from S-01/S-02: `Note` and `Card` aggregates, the generation pipeline, and `CardRepository.list_by_note` already exist. S-06 is primarily a **read-model + HTTP + TUI** slice — no new aggregates are expected.

**TUI and card read API do not exist yet.** The note list shows `card_count`, the note-detail screen renders content only, there are no `/cards` HTTP routes, no card OpenAPI types, and no card screens in the TUI.

## Findings

### Product requirement and traceability

S-06 maps to roadmap slice S-06 with acceptance criterion AC-12 only. It depends on S-04 (done) and unblocks S-05 (card-to-anchor jump).

- **AC-12:** "The cards generated from an open note are visible from that note." (`context/efforts/distill-flow/stories.md:64`)
- **FR-012:** "User can see the cards generated from an open note." — must-have (`context/efforts/distill-flow/prd.md:57`)
- **US-06** spans two slices: AC-11 (open note, read content) is S-04 done; AC-12 (see cards) is S-06 (`context/efforts/distill-flow/stories.md:57-64`, `context/efforts/distill-flow/roadmap.md:58-65`, `75-81`)
- The effort goal names "a readable note, its cards, and a jump from any card to the fragment it came from" — S-06 closes the "its cards" part; jump is S-05 (`context/efforts/distill-flow/effort.md:16`)

Navigation intent from the distill-pillar duck session is **selection-addressed**: `/notes` → list → Enter → note → a shortcut/command into its cards. `<note-id>` as a command argument is an alternative path, never the default gesture (`context/duck-sessions/distill-pillar/log.md:12`). The concrete product ask is seeing, in the TUI, that a card came into existence and which note it belongs to (`context/duck-sessions/distill-pillar/log.md:21`).

UI shape was decided at split time: cards are numerous enough to warrant a **separate scrollable list + expand view** screen, not embedded in note detail (`context/archive/changes/2026-09-06-distill-flow-note-detail/plan-brief.md:21`). The change stub names the expected surfaces: cards-list / card-detail screen (`context/changes/distill-flow-note-cards/change.md:15`).

### Scope boundary: S-04 vs S-06

S-04 (`distill-flow-note-detail`, archived) owns AC-11 only. During planning, AC-12 was carved out into S-06 so `GetNote` carries no card data at all (`context/archive/changes/2026-09-06-distill-flow-note-detail/plan.md:5`, `37-40`).

**S-04 done (do not re-implement in S-06):**

- `GET /notes/{note_id}` — note fields only, no `cards` field (`backend/src/application/distill/queries/get_note.py:20-28`)
- `NoteDetailScreen` — topic, tags, full content (`tui/src/screens/NoteDetailScreen.tsx:22-34`)
- Two-level overlay navigation: list ↔ detail, ESC stack (`tui/src/app.tsx:20-50`)
- Enter opens detail only for `ready` notes (`tui/src/screens/NoteListOverlay.tsx:37-41`)

**S-06 owns:**

- AC-12 — cards visible from an open note
- Cards-list + card-detail UI
- Backend read path for cards, separate from `GetNote` (`context/changes/distill-flow-note-cards/change.md:15`)
- Entry gesture from note detail into cards view (deferred from S-04 plan: `context/archive/changes/2026-09-06-distill-flow-note-detail/plan.md:40`)

**Out of scope for S-06:**

- Card-to-anchor jump (AC-13 / FR-013) — S-05 `distill-flow-card-anchor-jump` (`context/efforts/distill-flow/roadmap.md:67-73`)
- "Cards ready" one-time notification (FR-014) (`context/efforts/distill-flow/prd.md:59`, `71`)
- Manual card removal, regeneration, note editing, spaced repetition (`context/efforts/distill-flow/prd.md:63-66`)
- Discarded cards in any user-facing read (`context/adrs/distill-domain-shape/decision.md:124`)

### Domain layer

The distill bounded context lives at `backend/src/domain/distill/`. Two aggregates are defined per ADR (`context/adrs/distill-domain-shape/decision.md:27-41`):

**Note** (`backend/src/domain/distill/note.py:16-35`): topic, content, tags, `distillation_status`, timestamps. Factory `mint_note()` creates in `GENERATING`; `mark_ready()` / `mark_failed()` are terminal transitions.

**Card** (`backend/src/domain/distill/card.py:15-22`): `id`, `note_id`, `front`, `back`, `anchor`, optional `discard`, `created_at`. Live iff `discard is None` (`decision.md:41`, `46`). Invariant: front and back must differ (`card.py:24-27`).

Supporting value objects and ports:

| Kind | Name | Location |
|------|------|----------|
| IDs | `NoteId`, `CardId` | `backend/src/domain/distill/value_objects.py:20-25`, `63-66` |
| Sides | `CardSide` (max 2000) | `value_objects.py:69-83` |
| Anchor | `Anchor` (quote, max 4000) | `value_objects.py:86-102` |
| Discard | `DiscardReason`, `Discard` | `value_objects.py:105-119` |
| Port | `NoteRepository` — save, get, list_all | `backend/src/domain/distill/ports.py:8-13` |
| Port | `CardRepository` — save, list_by_note | `ports.py:16-19` |

Cards are generated asynchronously: `note_approved` → `SaveNoteCommand` → outbox `note_saved` → `FlashcardGenHandler` → `GenerateCardsCommand` → `CardFactory.mint` → `CardRepository.save` → `note.mark_ready()` (`backend/src/application/distill/commands/save_note.py:32-42`, `generate_cards.py:33-73`, `backend/src/domain/distill/card_factory.py:47-59`).

**Domain is complete for S-06.** The ADR explicitly left query DTOs and ordering outside the domain (`decision.md:115`, `161`). No new aggregates or domain changes are required for a "list live cards for note" read path — `list_by_note` plus application-side filter is the established pattern.

**Possibly needed only if card-detail requires fetch-by-id:**

- `CardRepository.get(card_id: CardId) -> Card | None` — not in `ports.py:16-19`
- `DistillCardNotFoundError` — not in `exceptions.py`

### Card data rules for user-facing reads

Every user-facing card read must filter `discard is None`. A missed filter would surface fabricated (ungrounded or oversized) cards (`decision.md:124`). The pattern is already applied in list-notes:

```15:18:backend/src/adapters/out/in_memory/distill/list_notes_query.py
            live_cards = [
                card
                for card in await self._card_repository.list_by_note(note.id)
                if card.discard is None
```

Proposed card read DTO (from pre-split research, not yet implemented):

| DTO field | Domain source |
|-----------|---------------|
| `card_id` | `Card.id.value` (`card.py:16`) |
| `front` | `Card.front.value` (`card.py:18`) |
| `back` | `Card.back.value` (`card.py:19`) |
| `anchor_quote` | `Card.anchor.quote` (`card.py:20`, `value_objects.py:87`) |
| `created_at` | `Card.created_at` (`card.py:22`) |

(`context/archive/changes/2026-09-06-distill-flow-note-detail/research.md:127-131`)

Zero cards on a `ready` note is success, not failure — differing only in card count (AC-04, FR-005: `stories.md:27-28`, `prd.md:47`). S-06 must handle empty card list gracefully.

Display of `anchor.quote` on card rows is in scope for S-06; anchor resolution for highlighting/jump is S-05 (`context/archive/changes/2026-09-06-distill-flow-note-detail/research.md:111-113`).

### Backend / API read surface

| Surface | Status | Evidence |
|---------|--------|----------|
| `GET /notes` with `card_count` (live only) | Exists | `backend/src/adapters/http/notes.py:17-21` |
| `GET /notes/{note_id}` (no cards) | Exists | `notes.py:24-29` |
| `GET /notes/{note_id}/cards` | Missing | No route in `backend/src/adapters/http/` |
| `ListCardsQueryPort` / card DTOs | Missing | Only `list_notes.py` and `get_note.py` under `application/distill/queries/` |
| BDD feature for US-06 / AC-12 | Missing | No US-06 feature file in `backend/tests/features/distill-flow/` |

`CardRepository.list_by_note` is implemented and wired (`backend/src/adapters/out/in_memory/distill/card_repository.py:8-16`, `compose.py:91-94`) but is only consumed internally by `list_notes_query` for counts. No HTTP integration tests for card list/detail exist.

ADR names a future "list cards for a note" query DTO, selection-addressed (`context/adrs/distill-domain-shape/research.md:90-92`). Most likely route shape: `GET /notes/{note_id}/cards` (nested under note, matches selection flow).

Greenfield work for S-06 backend:

1. `ListCardsForNoteQueryPort` + `CardListItemDTO` (live cards only)
2. Optional `GetCardQueryPort` + `CardDetailDTO` if card-detail is a separate screen
3. In-memory query adapter using `CardRepository.list_by_note` + live filter
4. HTTP route under notes router
5. OpenAPI regeneration

### TUI layer

**Current navigation (S-03 + S-04):**

```
CaptureScreen → /notes → NoteListOverlay → Enter (ready) → NoteDetailScreen
                                                      ESC → list → capture
```

(`tui/src/app.tsx:20-50`, `tui/src/screens/NoteListOverlay.tsx:22-42`)

**Expected S-06 extension:**

```
NoteDetailScreen → shortcut/command → CardsListScreen → Enter/expand → CardDetailScreen
                                    ESC ← detail ← list ← detail ← list ← capture
```

`app.tsx` today supports only one conditional inside the overlay (`isDetailOpen ? NoteDetailScreen : NoteListOverlay` at `app.tsx:49`). S-06 needs a third (and possibly fourth) view level and a deeper ESC stack.

| Element | Status | Reference |
|---------|--------|-----------|
| Note list with `cardCount` badge | Exists | `NoteListOverlay.tsx:95-97`, `tui/src/api/notes.ts:55` |
| Note detail (content only) | Exists | `NoteDetailScreen.tsx:22-34` |
| Cards list / card detail screens | Missing | No `Card*` under `tui/src/screens/` |
| Cards API client | Missing | `tui/src/api/notes.ts` has `listNotes` + `getNote` only |
| Card OpenAPI types | Missing | `schema.d.ts` — no `/cards` paths or card DTOs |
| App nav state for cards | Missing | `useAppStore` has no card-level fields (`tui/src/store/index.ts:3-16`) |
| Cards store | Missing | No `useCardsStore` |
| Entry gesture from note detail | Missing | Deferred to S-06 (`plan.md:40`) |
| Card screen/store tests | Missing | — |

**Patterns to follow from S-04:**

- Data store with fetch-on-navigate and error closes view: `tui/src/store/noteDetail.ts:15-32`
- Screen fetches on mount via `useEffect`: `NoteDetailScreen.tsx:11-15`
- List overlay: `useInput` + blue selection: `NoteListOverlay.tsx:22-42`, `90-91`
- API client: camelCase domain types, status-aware errors, snake_case mapping: `tui/src/api/notes.ts:24-58`
- Tests: seed Zustand state, mock API module (`tui/test/noteDetailScreen.test.tsx`, `noteDetailStore.test.ts`)

Greenfield work for S-06 TUI:

1. Regenerated OpenAPI types + `cards.ts` API module
2. `useCardsStore` (fetch by `noteId`, error surfaces to existing banner)
3. Extended `useAppStore` navigation (`isCardsOpen`, card selection, card-detail flags)
4. `CardListScreen` / `CardDetailScreen`
5. Entry gesture on `NoteDetailScreen`
6. Extended `app.tsx` routing and ESC stack
7. Tests mirroring note-detail conventions

## Code References

- `context/changes/distill-flow-note-cards/change.md:15` — owns cards-list/card-detail screen and backend read surface
- `context/efforts/distill-flow/roadmap.md:75-81` — S-06 slice definition, prereq S-04, blocks S-05
- `context/efforts/distill-flow/stories.md:64` — AC-12 acceptance criterion
- `context/efforts/distill-flow/prd.md:57` — FR-012 must-have
- `context/duck-sessions/distill-pillar/log.md:12` — selection-addressed navigation intent
- `context/archive/changes/2026-09-06-distill-flow-note-detail/plan.md:5,37-40` — GetNote has no cards; gesture deferred to S-06
- `context/archive/changes/2026-09-06-distill-flow-note-detail/plan-brief.md:21` — scrollable list + expand view
- `context/archive/changes/2026-09-06-distill-flow-note-detail/research.md:129` — proposed card DTO shape
- `context/adrs/distill-domain-shape/decision.md:41,46,124` — live card rule and read invariant
- `backend/src/domain/distill/card.py:15-22` — Card aggregate
- `backend/src/domain/distill/ports.py:16-19` — CardRepository port
- `backend/src/adapters/out/in_memory/distill/list_notes_query.py:15-18` — live-card filter pattern
- `backend/src/adapters/http/notes.py:17-29` — existing note HTTP routes
- `backend/src/application/distill/queries/get_note.py:20-28` — NoteDetailDTO (no cards)
- `tui/src/app.tsx:20-50` — overlay shell and two-level ESC
- `tui/src/screens/NoteListOverlay.tsx:37-41,95-97` — list navigation and card count display
- `tui/src/screens/NoteDetailScreen.tsx:22-34` — note content only, no cards
- `tui/src/store/index.ts:3-16` — app navigation state (no card fields)
- `tui/src/store/noteDetail.ts:15-32` — fetch-on-navigate store pattern
- `tui/src/api/notes.ts:24-58` — API client pattern to mirror for cards
- `tui/src/api/generated/schema.d.ts:75-108,255-273` — existing note types, no card types

## Open Questions

1. **Layout** — separate cards screen vs pane within note detail? Split decision points to separate screen (`plan-brief.md:21`), but `/plan` should confirm.
2. **Entry gesture** — which key/command from `NoteDetailScreen` opens cards? (`distill-pillar/log.md:12`, `plan.md:40`)
3. **Card detail UX** — expand-in-list vs dedicated card-detail screen ("expand view" in plan brief).
4. **HTTP shape** — `GET /notes/{note_id}/cards` vs `GET /cards?note_id=…`? Follow CQRS-lite query package conventions.
5. **Zero cards** — show cards screen with empty state, or disable entry when `cardCount === 0`?
6. **Polling** — refresh cards while cards view is open? Notes poll every 3s (`NoteListOverlay.tsx:7`).
7. **`CardRepository.get`** — needed only if card-detail requires fetch-by-id rather than selection from already-fetched list.
