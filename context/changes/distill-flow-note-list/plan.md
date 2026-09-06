# Note List Implementation Plan

## Overview

Deliver slice S-03 of the `distill-flow` effort: users can list their notes — topic, distillation state, live card count — without losing an in-flight capture session (FR-007 through FR-010). This adds the read path the domain shape ADR deliberately left open: a `ListNotes` query on the backend, and a TUI overlay reachable via `/notes` that layers over `CaptureScreen` without unmounting it.

## Current State Analysis

- `Note` (`backend/src/domain/distill/note.py`) has `topic`, `distillation_status` (`GENERATING`/`READY`/`FAILED`), `created_at`, `approved_at` — no recency field beyond those. `mark_ready()`/`mark_failed()` only transition from `GENERATING`.
- `GenerateCardsCommand.handle()` (`backend/src/application/distill/commands/generate_cards.py:50-73`) always saves every generated card (line 64) **before** calling `note.mark_ready()` (line 71); the failure branch (line 45) always precedes any card save. So within today's single call site, a note's state-transition timestamp is always the same instant as or later than every card it produced in that run.
- `CardRepository.list_by_note()` returns all cards including discarded ones; a card is live only while `discard is None` (`backend/src/domain/distill/card.py:21`).
- No `application/distill/queries/` package exists yet. The pattern is established elsewhere: `application/capture/queries/transcript.py` and `application/shared/outbox/queries/envelopes.py` — a `Protocol` port + a plain DTO, no `UnitOfWork`, no `commit()` (`context/foundation/rules/cqrs-lite.md`).
- The closest concrete precedent for a query-backed GET route is `backend/src/adapters/http/outbox.py:1-16` — route depends on the query's `Protocol` type via `Depends(get_*)`, returns the DTO list directly, no per-route error handling.
- `backend/src/adapters/compose.py` already holds singleton instances `_distill_note_repository` (`InMemoryDistillNoteRepository`) and `_distill_card_repository` (`InMemoryCardRepository`) — no wiring changes needed for those, only a new query adapter + factory.
- In-memory adapters (`note_repository.py`, `card_repository.py` under `adapters/out/in_memory/distill/`) are dict-backed with `snapshot()`/`restore()` for test isolation; `NoteRepository` has no scan-all method yet.
- `tui/src/app.tsx` renders only `<CaptureScreen />`, no other state. `CaptureScreen.tsx` dispatches `/approve` via a plain string-equality check inside `handleSubmit` (no command registry) and highlights the input via a parallel `isApproveCommand` boolean.
- `tui/src/store/chat.ts` is a single flat Zustand slice (`create<ChatState & ChatActions>(...)`). `tui/src/store/index.ts` already exports a second, currently-empty store (`useAppStore = create(() => ({}))`) — multi-store is already the established shape, not a new pattern.
- `tui/src/api/client.ts` exports one shared typed `openapi-fetch` client reused by `stream.ts`'s typed calls (`startCaptureSession`, `approveNote`); both throw a plain `Error` on failure when no typed error body is present.
- No `useInput` (Ink's keyboard-input hook) usage exists anywhere in `tui/src` or `tui/test` — ESC-to-close will be the first use of this hook in the codebase.
- Tests use `ink-testing-library`'s `render()` + `stdin.write(...)` + a hand-rolled `waitFor`/`waitForFrame` poll (real timers, 20ms steps, 2s timeout) for interaction; API calls are mocked via `vi.mock("../src/api/stream", ...)`; store state is seeded directly with `useXStore.setState(...)`. No mock-service library (e.g. MSW) is in use anywhere — `stream.test.ts` mocks at the global `fetch` level via `vi.stubGlobal`.

## Desired End State

`GET /notes` returns every note as a `NoteListItemDTO` (topic, raw distillation status, live card count, last-updated timestamp), ordered most-recent-first. In the TUI, typing `/notes` opens `NoteListOverlay` over the still-mounted `CaptureScreen`; each row shows topic, a three-way status badge (generating — with elapsed age, ready, or failed), and card count; the overlay polls while open so a `GENERATING` row can flip to `READY`/`FAILED` live; ESC closes it. No field in `useChatStore` (`sessionId`, `transcript`, `topic`, `coverageConfidence`, `draft`, `currentReply`, `isStreaming`) changes value across an open/close cycle.

Verify: run the backend (`uv run fastapi dev src/main.py`) and the TUI (`pnpm dev` or built `weles` binary); approve a note through capture, type `/notes`, confirm it appears with the right badge and card count; press ESC; confirm the capture screen's in-progress state (topic/draft/transcript, if any) is exactly as it was before opening the overlay.

### Key Discoveries

- `generate_cards.py:64` (card save) always precedes `:71` (`mark_ready()`) in the same handler run — this is why recency can be computed at read time from `note.updated_at` and each live card's existing `created_at`, without any aggregate needing to reach across the other's repository.
- `adapters/http/outbox.py` + `adapters/compose.py:181-182` (`get_outbox_envelope_query`) is the exact shape to mirror for `GET /notes`'s route and factory wiring.
- `tui/src/store/index.ts`'s `useAppStore` is already a second, live Zustand store — adding overlay-open state there is not a new pattern.
- Ink has no z-index/compositing — "overlay" means conditionally rendering `NoteListOverlay` alongside `CaptureScreen` in the same `Box`/fragment, not true layering.

## What We're NOT Doing

- Note detail / open-note reading (S-04, FR-011/012) and card-to-anchor jump (S-05, FR-013).
- The one-time "cards ready" notification (FR-014) — explicitly deferred; the badge on the list carries the fact instead.
- Pagination or a result cap on `GET /notes` — returns the full list (decided: MVP scale, single user, in-memory store).
- Any change to the `Card` domain model, and no cross-aggregate write from `CardRepository` into `Note` — recency from card activity is computed at read time only, never persisted onto `Note` by anything other than `Note`'s own methods.
- A sweeper or retry for notes stuck in `GENERATING` — the list only ever shows a badge (with elapsed age); no timeout logic.
- Any SQL or other durable adapter — in-memory only, per `InMemoryFirst`.
- Whole-effort non-goals: spaced repetition, manual card removal, regeneration, note editing, external publishing, a rejected-proposals surface, semantic search, non-capture note origins.

## Implementation Approach

A backend-first vertical slice, each TDD'able unit split into a stubs-and-interfaces phase followed by a behavior phase (the exported symbol must exist before a test can import it):

1. **Domain recency** — `Note.updated_at`, bumped only by the aggregate's own methods (`mint_note`/`mark_ready`/`mark_failed`) through a private `_touch`. Nothing outside `Note` ever writes this field.
2. **Read model** — `ListNotesQueryPort` + `NoteListItemDTO` (new `application/distill/queries/` package, mirroring `capture`'s and `shared/outbox`'s existing query packages) and an in-memory adapter that reads both repositories directly into DTOs (CQRS-lite: no `UnitOfWork`). The adapter computes the sort key as `max(note.updated_at, max(live card.created_at))` — reusing `Card.created_at`, no new Card field — so a future card-write path that doesn't coincide with a note transition is still handled correctly by reading, never by a repository mutating another aggregate.
3. **HTTP** — `GET /notes` mirroring `outbox.py`'s shape exactly (`Depends` on the query `Protocol`, DTO list returned as-is), registered unconditionally in `main.py` (this is a real user-facing route, unlike the dev-only `/_outbox`).
4. **TUI** — typed client → dedicated `useNotesStore` + a `useNotesPolling` hook (poll starts/stops with the overlay component's mount/unmount, so no separate open/close-orchestration layer is needed) → app shell wiring (`/notes` dispatch, conditional render, first `useInput`-based ESC handler) → presentational `NoteListOverlay`.

## Phase 1: Note recency — interfaces

### Overview

Add the exported symbols a domain test will need to import, with no behavior yet.

### Changes Required:

#### 1. Note aggregate — recency field and private hook

**File**: `backend/src/domain/distill/note.py`

**Intent**: Give `Note` a recency timestamp it alone controls.

**Contract**: `Note` gains `updated_at: datetime`. A new private method `_touch(self, at: datetime) -> None` exists but is not yet called from anywhere (`mint_note`, `mark_ready`, `mark_failed` unchanged this phase).

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/test_note.py` (existing suite still green — no behavior changed yet)
- `cd backend && uv run basedpyright src/domain/distill/note.py`

---

## Phase 2: Note recency — wiring

### Overview

Wire `_touch` into the aggregate's own transition points; this is the only place `updated_at` is ever written.

#### Tests

- [ ] tests generated

### Changes Required:

#### 1. Note aggregate — bump on mint and transition

**File**: `backend/src/domain/distill/note.py`

**Intent**: `updated_at` reflects the note's own lifecycle, set once at minting and refreshed on every legal state transition.

**Contract**: `mint_note(...)` sets `updated_at` equal to the same instant as `created_at`. `mark_ready()` and `mark_failed()` each call `self._touch(datetime.now(UTC))` after their existing transition check, before returning. No other method calls `_touch`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/test_note.py` — covers: `mint_note` sets `updated_at`; `mark_ready` and `mark_failed` each bump it forward; `_ensure_generating`'s existing `InvalidDistillationTransitionError` guard still fires (and does not bump `updated_at`) on a repeat call.

---

## Phase 3: ListNotes read model — interfaces

### Overview

Materialize the read-side symbols: the DTO, the query port, and the port method the in-memory adapter will need, none implemented yet.

### Changes Required:

#### 1. Query port and DTO

**File**: `backend/src/application/distill/queries/list_notes.py` (new)

**Intent**: Mirror the established query-package shape (`application/shared/outbox/queries/envelopes.py`) for the distill context's first query.

**Contract**:
```python
class NoteListItemDTO(BaseModel):
    note_id: UUID
    topic_label: str
    distillation_status: str
    card_count: int
    last_updated_at: datetime

class ListNotesQueryPort(Protocol):
    async def list_notes(self) -> list[NoteListItemDTO]: ...
```

#### 2. Repository scan method

**File**: `backend/src/domain/distill/ports.py`

**Intent**: `NoteRepository` needs a way to enumerate every note for the list read model.

**Contract**: `NoteRepository` Protocol gains `async def list_all(self) -> list[Note]: ...`.

#### 3. In-memory scan implementation (stub)

**File**: `backend/src/adapters/out/in_memory/distill/note_repository.py`

**Intent**: Satisfy the new port method signature; body deferred to the behavior phase.

**Contract**: `InMemoryNoteRepository.list_all()` exists with the correct signature (may raise `NotImplementedError` or return `[]`).

#### 4. Query adapter skeleton

**File**: `backend/src/adapters/out/in_memory/distill/list_notes_query.py` (new)

**Intent**: Materialize the concrete adapter class the behavior phase will fill in.

**Contract**: `InMemoryListNotesQuery(note_repository: NoteRepository, card_repository: CardRepository)` implementing `ListNotesQueryPort`, `list_notes()` unimplemented.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright src/application/distill/queries/list_notes.py src/adapters/out/in_memory/distill/list_notes_query.py`

---

## Phase 4: ListNotes read model — logic

### Overview

Implement the read model: live-card filtering, three-way status exposure, and recency-based ordering.

#### Tests

- [ ] tests generated

### Changes Required:

#### 1. Repository scan implementation

**File**: `backend/src/adapters/out/in_memory/distill/note_repository.py`

**Intent**: Return every stored note for the read model to consume.

**Contract**: `list_all()` returns `list(self._notes.values())`.

#### 2. Query adapter logic

**File**: `backend/src/adapters/out/in_memory/distill/list_notes_query.py`

**Intent**: Produce one DTO per note: live card count (excluding discarded), raw distillation status (the TUI maps the three display cases — generating / ready-with-zero / failed — from `distillation_status` + `card_count`, not this adapter), and a recency-ordered list.

**Contract**: For each note from `note_repository.list_all()`: live cards = `[c for c in await card_repository.list_by_note(note.id) if c.discard is None]`; `card_count = len(live cards)`; sort key = `max(note.updated_at, max((c.created_at for c in live cards), default=note.updated_at))`; return DTOs sorted by that key descending.

#### 3. Contract test coverage

**File**: `backend/tests/unit/distill/contracts/test_note_repository_contract.py`

**Intent**: `list_all()` is a port method — it needs a contract-test case per `context/foundation/rules/contract-testing.md`.

**Contract**: Add a case asserting `list_all()` returns every saved note (order-independent).

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/contracts/test_note_repository_contract.py` — covers `list_all()`.
- `cd backend && uv run pytest tests/unit/distill -k list_notes` — covers: zero-notes case; three-way status exposure (generating / ready+0 cards / failed); discarded cards excluded from `card_count`; ordering by recency, including a case where a later-generated card would have been more recent than its note's own last transition if not for the always-transition-after-save ordering (i.e. the `max()` still produces the correct order under a fabricated adversarial timestamp).

---

## Phase 5: `GET /notes` route — interfaces

### Overview

Add the route and compose wiring, unimplemented body.

### Changes Required:

#### 1. Route skeleton

**File**: `backend/src/adapters/http/notes.py` (new)

**Intent**: Mirror `adapters/http/outbox.py`'s shape for the new query.

**Contract**: `router = APIRouter()`; `@router.get("/notes") async def list_notes(query: Annotated[ListNotesQueryPort, Depends(get_list_notes_query)]) -> list[NoteListItemDTO]` — body raises `NotImplementedError` this phase.

#### 2. Compose factory skeleton

**File**: `backend/src/adapters/compose.py`

**Intent**: Wire the new query adapter as a singleton, same shape as `get_outbox_envelope_query`.

**Contract**: `_list_notes_query = InMemoryListNotesQuery(_distill_note_repository, _distill_card_repository)` module singleton; `def get_list_notes_query() -> ListNotesQueryPort: return _list_notes_query`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright src/adapters/http/notes.py src/adapters/compose.py`

---

## Phase 6: `GET /notes` route — wiring

### Overview

Complete the route body, register it, and regenerate the TUI's OpenAPI schema.

#### Tests

- [ ] tests generated

### Changes Required:

#### 1. Route body

**File**: `backend/src/adapters/http/notes.py`

**Intent**: Delegate straight to the query, no mapping step (CQRS-lite: the DTO the adapter serializes is the DTO the query returns).

**Contract**: `return await query.list_notes()`.

#### 2. Router registration

**File**: `backend/src/main.py`

**Intent**: `/notes` is a production route, unlike the dev-only `/_outbox` — register unconditionally.

**Contract**: `app.include_router(notes_router)` alongside `capture_router`, no `Environment` gate.

#### 3. Integration test

**File**: `backend/tests/integration/test_notes_http.py` (new)

**Intent**: Prove the HTTP contract end to end against the real app.

**Contract**: Add a `notes_client` fixture to `tests/integration/conftest.py` (mirroring `outbox_client`, exposing the underlying `InMemoryDistillNoteRepository`/`InMemoryCardRepository` for test setup); assert `GET /notes` returns `200` with the seeded notes' shape and ordering.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/integration/test_notes_http.py`

#### Manual Verification:
- `cd backend && uv run fastapi dev src/main.py`, then `curl localhost:8000/notes` and confirm the JSON shape.
- `cd tui && pnpm generate:api` (with the backend above running) and confirm `src/api/generated/schema.d.ts` gains a `/notes` path.

---

## Phase 7: Notes API client — interfaces

### Overview

Add the typed client function signature, unimplemented.

### Changes Required:

#### 1. Client module skeleton

**File**: `tui/src/api/notes.ts` (new)

**Intent**: Mirror `stream.ts`'s `startCaptureSession` shape for a typed GET.

**Contract**:
```ts
export type NoteListItem = {
  noteId: string;
  topicLabel: string;
  distillationStatus: "generating" | "ready" | "failed";
  cardCount: number;
  lastUpdatedAt: string;
};

export async function listNotes(): Promise<NoteListItem[]>;
```
Body throws (unimplemented) this phase.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm typecheck`

---

## Phase 8: Notes API client — behavior

### Overview

Implement the request and snake_case→camelCase mapping.

#### Tests

- [ ] tests generated

### Changes Required:

#### 1. Client implementation

**File**: `tui/src/api/notes.ts`

**Intent**: Call the shared typed client and map the DTO's snake_case fields to the camelCase `NoteListItem` shape, following `startCaptureSession`'s error-on-failure convention (no typed error body expected for this route, so a plain `Error` on failure).

**Contract**: `const { data, error } = await client.GET("/notes"); if (error || !data) throw new Error("Failed to list notes"); return data.map((item) => ({ noteId: item.note_id, topicLabel: item.topic_label, distillationStatus: item.distillation_status, cardCount: item.card_count, lastUpdatedAt: item.last_updated_at }));`

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm vitest run test/notes.test.ts` (new file, mirroring `stream.test.ts`'s `vi.stubGlobal("fetch", ...)` convention) — covers: successful mapping of a multi-item response; thrown `Error` on a non-ok response.

---

## Phase 9: Notes data store — interfaces

### Overview

Materialize the store and hook signatures.

### Changes Required:

#### 1. Store skeleton

**File**: `tui/src/store/notes.ts` (new)

**Intent**: Dedicated store for note-list data, separate from `chat.ts` (confirmed: notes gets its own store, not a slice merged into chat).

**Contract**:
```ts
type NotesState = {
  items: NoteListItem[];
  isLoading: boolean;
  error: string | null;
};
type NotesActions = {
  fetchNotes: () => Promise<void>;
  startPolling: (intervalMs: number) => void;
  stopPolling: () => void;
};
export const useNotesStore = create<NotesState & NotesActions>(...);
```
Actions unimplemented this phase.

#### 2. Polling hook skeleton

**File**: `tui/src/hooks/useNotesPolling.ts` (new)

**Intent**: Encapsulate poll lifecycle as a reusable hook (the "shared actions" concern), tied to whichever component mounts it rather than to a separate open/close-orchestration layer — the overlay component's own mount/unmount already corresponds to open/close since `App` only renders it while `isNotesOverlayOpen` is true.

**Contract**: `export function useNotesPolling(intervalMs: number): void` — unimplemented body this phase.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm typecheck`

---

## Phase 10: Notes data store — behavior

### Overview

Implement fetch, poll start/stop, and the inline-error-with-auto-retry behavior.

#### Tests

- [ ] tests generated

### Changes Required:

#### 1. Store implementation

**File**: `tui/src/store/notes.ts`

**Intent**: `fetchNotes` loads and maps `listNotes()` results into state; a failure sets `error` without clearing prior `items` (so the last-known list stays visible under an inline error), and is not retried by the store itself — retry-on-next-tick is `startPolling`'s interval continuing to fire, not special-cased error-recovery code.

**Contract**: `fetchNotes` sets `isLoading: true`, calls `listNotes()`, on success sets `items` and clears `error`; on thrown error sets `error: message` and leaves `items` untouched; always ends with `isLoading: false`. `startPolling(intervalMs)` calls `fetchNotes()` immediately, then `setInterval(fetchNotes, intervalMs)`, storing the interval id. `stopPolling()` clears that interval id.

#### 2. Hook implementation

**File**: `tui/src/hooks/useNotesPolling.ts`

**Intent**: Start polling on mount, stop on unmount — no dependency on overlay-open state beyond the caller's own lifecycle.

**Contract**: `useEffect(() => { useNotesStore.getState().startPolling(intervalMs); return () => useNotesStore.getState().stopPolling(); }, [intervalMs])`.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm vitest run test/notesStore.test.ts` (new file) — using `vi.useFakeTimers()` + a mocked `tui/src/api/notes.ts` (per the agreed approach: fake timers plus module mocking, consistent with the existing `vi.stubGlobal` convention rather than a new mock-service library): covers `startPolling` firing an immediate fetch then one per interval tick; `stopPolling` halting further fetches; a failed fetch setting `error` while a subsequent successful tick clears it and updates `items`.

---

## Phase 11: Overlay shell + dispatch — interfaces

### Overview

Materialize the app-level state and dispatch symbols, unimplemented.

### Changes Required:

#### 1. App-level overlay state

**File**: `tui/src/store/index.ts`

**Intent**: `isNotesOverlayOpen` is UI-shell state, not note data — it belongs on the already-existing `useAppStore`, not the new `useNotesStore`.

**Contract**: `useAppStore` gains `isNotesOverlayOpen: boolean` (initial `false`), `openNotes: () => void`, `closeNotes: () => void` — actions unimplemented this phase (or trivially set the flag; either is acceptable stub state).

#### 2. Slash-command constant

**File**: `tui/src/screens/CaptureScreen.tsx`

**Intent**: Add `/notes` alongside `/approve`'s existing exact-match dispatch style (no command registry in this codebase).

**Contract**: `const NOTES_COMMAND = "/notes";` declared; not yet branched on in `handleSubmit`.

#### 3. App shell overlay slot

**File**: `tui/src/app.tsx`

**Intent**: Prepare the conditional-render branch and the first `useInput`-based key handler in this codebase.

**Contract**: `App` reads `isNotesOverlayOpen`/`closeNotes` from `useAppStore`; imports `useInput` from `ink` (handler body deferred to the behavior phase); JSX still renders only `<CaptureScreen />` this phase.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm typecheck`

---

## Phase 12: Overlay shell + dispatch — wiring

### Overview

Wire `/notes` to open the overlay, ESC to close it, and confirm `CaptureScreen` never unmounts and its state never resets.

#### Tests

- [ ] tests generated

### Changes Required:

#### 1. Store actions

**File**: `tui/src/store/index.ts`

**Intent**: `openNotes`/`closeNotes` flip the flag.

**Contract**: `openNotes: () => set({ isNotesOverlayOpen: true })`, `closeNotes: () => set({ isNotesOverlayOpen: false })`.

#### 2. Dispatch branch

**File**: `tui/src/screens/CaptureScreen.tsx`

**Intent**: `/notes` opens the overlay the same way `/approve` triggers its action — an equality branch in `handleSubmit`, plus the matching input-highlight boolean.

**Contract**: `if (trimmed === NOTES_COMMAND) { useAppStore.getState().openNotes(); return; }` added before the existing `/approve` branch check (order doesn't matter, values are mutually exclusive); `isNotesCommand = inputValue.trim() === NOTES_COMMAND` mirroring `isApproveCommand`.

#### 3. App shell render + ESC

**File**: `tui/src/app.tsx`

**Intent**: Host `NoteListOverlay` without unmounting `CaptureScreen`; ESC closes it.

**Contract**: `<><CaptureScreen />{isNotesOverlayOpen && <NoteListOverlay />}</>`; `useInput((_input, key) => { if (key.escape && isNotesOverlayOpen) closeNotes(); })`.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm vitest run test/app.test.tsx` (extended) — covers: typing `/notes` then Enter causes the overlay's presence to be detectable in the rendered frame; pressing ESC afterward removes it; before/after comparing every `useChatStore` field (`sessionId`, `transcript`, `topic`, `coverageConfidence`, `draft`, `currentReply`, `isStreaming`) shows no change across the open/close cycle.

---

## Phase 13: `NoteListOverlay` — interfaces

### Overview

Materialize the component and its status-badge helper signature.

### Changes Required:

#### 1. Component skeleton

**File**: `tui/src/screens/NoteListOverlay.tsx` (new)

**Intent**: Presentational component reading `useNotesStore`, driving `useNotesPolling`.

**Contract**: `export default function NoteListOverlay(): JSX.Element` — renders a placeholder; calls `useNotesPolling(NOTES_POLL_INTERVAL_MS)` (constant `= 3000`).

#### 2. Badge mapping helper skeleton

**File**: `tui/src/screens/NoteListOverlay.tsx`

**Intent**: Isolate the three-way display mapping (FR-010) as a pure, private, testable function — declared after the public component per `context/foundation/rules/code-ordering.md`.

**Contract**: `function statusBadge(item: NoteListItem, now: Date): string` — unimplemented this phase.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm typecheck`

---

## Phase 14: `NoteListOverlay` — rendering

### Overview

Implement row rendering: topic, three-way badge (with elapsed age on generating), card count, and the inline error state.

#### Tests

- [ ] tests generated

### Changes Required:

#### 1. Badge mapping logic

**File**: `tui/src/screens/NoteListOverlay.tsx`

**Intent**: Map raw `distillationStatus` + `cardCount` to the three product-facing cases from FR-010: generating (with elapsed age), completed with zero cards, completed with cards (implicit — just the count), failed.

**Contract**: `distillationStatus === "generating"` → `"Generating (<age>)"` where age is a human-readable elapsed time from `lastUpdatedAt` to `now`; `"failed"` → `"Failed"`; `"ready"` → no separate badge text beyond the row's card count (zero-card ready is distinguished by `cardCount === 0`, not a special badge string).

#### 2. Row rendering

**File**: `tui/src/screens/NoteListOverlay.tsx`

**Intent**: One row per item: topic, badge, card count; an inline error line when `error` is set (list stays visible underneath); a loading indicator only when `items` is still empty and `isLoading` is true (first load).

**Contract**: Iterates `useNotesStore((s) => s.items)`, rendering `topicLabel`, `statusBadge(item, new Date())`, and `cardCount` per row; renders `error` inline above the list when non-null.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm vitest run test/noteListOverlay.test.tsx` (new file, seeding `useNotesStore.setState(...)` directly per the existing store-seeding convention) — covers: a generating row shows its badge with elapsed age; a ready+zero-cards row is visually distinguishable from a ready+N-cards row; a failed row shows "Failed"; an inline error renders alongside a still-visible prior list; an empty list renders a loading indicator only while `isLoading` and `items` are both empty.

---

## Testing Strategy

### Unit Tests:
Domain (`Note` recency), read-model adapter (status/count/ordering logic), TUI client mapping, TUI store (fetch/poll/error-retry with fake timers), TUI component rendering (badge mapping, error/loading states) — one behavior phase's `#### Tests` row per unit above.

### Integration Tests:
`backend/tests/integration/test_notes_http.py` — the route contract end to end against the real FastAPI app. `tui/test/app.test.tsx` — the overlay open/close/dispatch flow and capture-state-preservation guarantee, via `ink-testing-library`.

### Manual Testing Steps:
Run backend + TUI together; approve a note; type `/notes`; observe the badge transition from generating to ready/failed as the backend's outbox-driven generation completes (poll picks it up); press ESC; confirm the capture screen is exactly as left.

## References

- `context/changes/distill-flow-note-list/research.md` — full FR/domain/TUI extraction with line-level citations.
- `context/efforts/distill-flow/prd.md:52-55` — FR-007 through FR-010.
- `context/adrs/distill-domain-shape/decision.md:27-32,42,46,107-108,116,124,134,161` — Note/Card shape, query-DTO scope left open, no cross-context imports.
- `context/adrs/tui-stack/decision.md:17-20,30` — Zustand, openapi-fetch, background polling.
- `backend/src/adapters/http/outbox.py`, `backend/src/application/shared/outbox/queries/envelopes.py`, `backend/src/adapters/out/in_memory/shared/outbox/envelope_query.py` — the query/route/adapter shape this plan mirrors.
