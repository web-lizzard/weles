# Remember Flow Review Session TUI Implementation Plan

## Overview

Add a **sitting overlay** to the TUI: typing `/remember` in the capture input opens an
absolute-positioned overlay (mirroring the existing `/notes` → `NoteListOverlay` pattern) that
drives the already-implemented `remember` HTTP surface end to end — open a sitting, show a
card's front, toggle its back on and off, grade it with either of two independent input paths,
advance through the sitting, and land on a "nothing due", "complete", or error state.

## Current State Analysis

- The backend side of this feature (`remember-flow-review-session`) is implemented and green:
  `POST /review-sittings`, `GET /review-sittings/{id}/cards/{id}/back`, and
  `POST /review-sittings/{id}/cards/{id}/grade` are live in
  `backend/src/adapters/http/remember.py:30-63`. `GET .../current-card` exists but this overlay
  never calls it — opening already returns the first card, and grading already returns the
  next one.
- `tui/src/api/generated/schema.d.ts` has no `/review-sittings...` paths yet — it was last
  generated before the backend routes landed. It must be regenerated against a running backend
  before the API client can be typed against it (same tooling `cards.ts` already uses).
- The TUI has three established per-domain layers to follow: `api/<domain>.ts` (thin fetch
  wrapper mapping snake_case → camelCase, see `api/cards.ts`, `api/notes.ts`), a
  `store/<domain>.ts` Zustand store owning async/domain state (`store/notes.ts`), and a
  `screens/<Name>Overlay.tsx` component. App-shell concerns (which overlay is open) live
  separately in `store/index.ts` (`isNotesOverlayOpen` etc.), not in the domain store.
- Structured HTTP errors already have a precedent: `api/stream.ts:63-71`'s
  `SendMessageHttpError extends Error` carries `code`/`detail`/`status`, is thrown when the
  response body matches `{code, detail}`, and is caught in `store/chat.ts` to populate a
  `{code, detail}` state field rendered by a `StatusBar`-style component
  (`screens/CaptureScreen.tsx:221-227`).
- `app.tsx:24-37`'s single `useInput` ESC handler already branches on which overlay/detail view
  is open, closing the innermost one first.

### Key Discoveries:

- `application/remember/dto.py:13-18`'s `PresentedCardDTO` — and by extension
  `SittingOpenedDTO` — carries `card_id: UUID | None` and `front: str | None`, an in-flight
  fix (uncommitted at plan time) so a just-completed sitting reports `sitting_complete: true`
  with no card rather than raising. This plan treats that shape as given.
- `POST /review-sittings` takes no request body (`adapters/compose.py:258-265`'s
  `OpenSittingCommand` needs no per-call input) — opening a sitting is parameterless from the
  TUI's side.
- `GradeAppliedDTO` (`application/remember/dto.py:35-39`) already returns
  `next_card_id`/`next_front` inline, so grading never needs a follow-up `current-card` call.
- `domain/remember/value_objects.py:9-13`'s `Grade` enum is exactly
  `forgot | hard | good | easy` — matches FR-04 one to one.
- `adapters/http/errors.py:8-51`'s exception map covers every sitting-flow error FR-06 names
  (`sitting_not_found`, `card_not_in_sitting`, `card_not_presentable`,
  `sitting_already_complete`, `card_not_reviewable`) plus `empty_sitting` /
  `invalid_showing_limit`; none of them need special-casing beyond generic `{code, detail}`
  display.

## Desired End State

Typing `/remember` opens the sitting overlay. It opens a sitting immediately; shows "nothing
due" when none is; otherwise shows the current card's front. `t` toggles the back on and off at
any time (fetched once per card, then reused). Grading works identically regardless of whether
the back is showing: number keys `1`-`4` grade immediately, or arrow up/down moves a
highlighted selection among the four grades with Enter confirming it. A successful grade
advances to the next presented card or a completion state. Any failed request shows a
`{code, detail}` message with a retry keypress that re-issues exactly the action that failed.
ESC closes the overlay from any state.

Verify with: `cd tui && pnpm test` green, plus a manual run against the live backend
(`cd backend && uv run fastapi dev src/main.py`, then the TUI) working through a full sitting.

### Key Discoveries:
(see above — folded in since both sections draw from the same investigation)

## What We're NOT Doing

- No queue size / progress indicator — the backend exposes no count (frame, out of scope).
- No coordination with `tui-card-detail-review` — confirmed independent, no shared component.
- No resume-across-reopen state — every `/remember` opens a fresh sitting via `OpenSittingCommand`.
- No `current-card` query call — open and grade responses already carry the current card.
- No change to the backend — `remember-flow-review-session` owns that surface.

## Implementation Approach

Bottom-up: the API client first (it has nothing else to depend on), then the store (depends on
the API client's types and functions), then the overlay screen (depends on the store), then the
one-line wiring into `CaptureScreen`/`app.tsx`/`store/index.ts` that makes it reachable. Each of
the first three units is TDD'able (API request/response contracts; a state machine; UI behaviour
exercised through `ink-testing-library`, per this repo's own convention for `NoteListOverlay`)
and — since no `discover-contracts.md` exists for this change — gets a stubs phase before its
behaviour phase, per `references/tdd-ability.md`. The screen's behaviour is split across two
phases (happy path; terminal/edge states) to keep each phase's test count inside this repo's
1-5-per-phase TUI convention. The final wiring phase touches only already-stubbed/behaviour-complete
files and needs no stub phase of its own.

```
CaptureScreen "/remember" ──▶ store/index.ts (isSittingOverlayOpen)
                                       │
app.tsx (absolute overlay) ───────────┴──▶ screens/SittingOverlay.tsx
                                                    │
                                            store/sitting.ts (phase, card, grade selection, retry)
                                                    │
                                            api/sittings.ts (openSitting / revealBack / gradeCard)
                                                    │
                                    POST /review-sittings · GET .../back · POST .../grade
```

## Critical Implementation Details

Grading must stay reachable regardless of `isBackVisible` — `t` only toggles a display flag,
never a gate on the grade actions. `toggleBack` fetches the back at most once per presented
card (caches it in state) so repeated toggling never re-issues the HTTP call.

## Phase 1: API client stubs

### Overview

Signatures for the sitting-flow API module the store will import.

### Changes Required:

#### 1. Regenerate the OpenAPI schema

**File**: `tui/src/api/generated/schema.d.ts`

**Intent**: Pick up the three `/review-sittings...` paths so the client can be typed against
them, matching how `api/cards.ts` and `api/notes.ts` already work.

**Contract**: Run the backend, then `cd tui && pnpm generate:api`. No manual edits to the
generated file.

#### 2. Sitting API module signatures

**File**: `tui/src/api/sittings.ts`

**Intent**: One thin module per the `api/cards.ts` / `api/stream.ts` precedent — camelCase DTOs
and a structured HTTP error type, function bodies not yet filled.

**Contract**:

```ts
export type Grade = "forgot" | "hard" | "good" | "easy";
export type OpenedSitting = {
  kind: "opened";
  sittingId: string;
  cardId: string;
  front: string;
  sittingComplete: boolean;
};
export type NothingDue = { kind: "nothing_due" };
export type RevealedCard = {
  sittingId: string;
  cardId: string;
  front: string;
  back: string;
};
export type GradeApplied = {
  sittingId: string;
  sittingComplete: boolean;
  nextCardId: string | null;
  nextFront: string | null;
};
export class SittingHttpError extends Error {
  constructor(public code: string, public detail: string, public status: number);
}
export async function openSitting(): Promise<OpenedSitting | NothingDue>;
export async function revealBack(
  sittingId: string,
  cardId: string,
): Promise<RevealedCard>;
export async function gradeCard(
  sittingId: string,
  cardId: string,
  grade: Grade,
): Promise<GradeApplied>;
```

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm typecheck`

#### Manual Verification:
- Open `tui/src/api/generated/schema.d.ts` and confirm `"/review-sittings"`,
  `"/review-sittings/{sitting_id}/cards/{card_id}/back"`, and
  `"/review-sittings/{sitting_id}/cards/{card_id}/grade"` are present.

---

## Phase 2: API client behaviour

### Overview

Fill `api/sittings.ts` bodies; prove the request/response mapping and error path.

### Changes Required:

#### 1. Fill the sitting API functions

**File**: `tui/src/api/sittings.ts`

**Intent**: `openSitting` distinguishes the two DTO shapes by the backend's `kind` discriminant;
`revealBack` and `gradeCard` map snake_case fields to camelCase; any non-2xx response with a
`{code, detail}` body throws `SittingHttpError`, per `api/stream.ts:88-97`'s precedent.

**Contract**: Same exported surface as Phase 1; no new symbols.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm vitest run test/sittings.test.ts`
- `cd tui && pnpm test`

---

## Phase 3: Sitting store stubs

### Overview

Signatures for the Zustand store owning sitting-flow state — the state machine the overlay
renders and the wiring phase resets on close.

### Changes Required:

#### 1. Sitting store signatures

**File**: `tui/src/store/sitting.ts`

**Intent**: One store per domain, per `store/notes.ts`'s precedent. Grading is always
reachable once a card is presented; `isBackVisible` is a pure display flag, never a gate.

**Contract**:

```ts
type SittingPhase = "opening" | "nothing_due" | "presented" | "complete" | "error";
type LastAction =
  | { type: "open" }
  | { type: "reveal" }
  | { type: "grade"; grade: Grade };

type SittingState = {
  phase: SittingPhase;
  sittingId: string | null;
  cardId: string | null;
  front: string | null;
  back: string | null;
  isBackVisible: boolean;
  selectedGradeIndex: number;
  isSubmitting: boolean;
  error: { code: string; detail: string } | null;
  lastAction: LastAction | null;
};

type SittingActions = {
  open: () => Promise<void>;
  toggleBack: () => Promise<void>;
  moveSelection: (delta: 1 | -1) => void;
  submitGrade: (grade: Grade) => Promise<void>;
  retry: () => Promise<void>;
  reset: () => void;
};
```

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm typecheck`

---

## Phase 4: Sitting store behaviour

### Overview

Fill the store; prove every transition in the state machine.

### Changes Required:

#### 1. Fill the sitting store

**File**: `tui/src/store/sitting.ts`

**Intent**: `open()` calls `openSitting()` and sets `nothing_due` or `presented` (resetting
`isBackVisible`/`back`/`selectedGradeIndex`/`error` for the new card). `toggleBack()` flips
`isBackVisible`; the first flip-to-visible for a card calls `revealBack()` and caches `back`,
later flips reuse it. `submitGrade(grade)` calls `gradeCard()`; on success it either re-presents
the next card (same reset as `open()`) or sets `complete`. Any of the three API calls failing
sets `phase: "error"` with `{code, detail}` from the thrown `SittingHttpError`, recording
`lastAction` beforehand so `retry()` can re-issue exactly that call. `reset()` returns to the
initial state (called on overlay close).

**Contract**: Same exported surface as Phase 3; no new symbols.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm vitest run test/sittingStore.test.ts`
- `cd tui && pnpm test`

---

## Phase 5: Sitting overlay stubs

### Overview

Signatures for the overlay screen and its state-specific sub-views.

### Changes Required:

#### 1. Sitting overlay component signature

**File**: `tui/src/screens/SittingOverlay.tsx`

**Intent**: One overlay screen per the `NoteListOverlay` precedent — a default export mounted
by `app.tsx`, plus module-private render helpers per phase (`opening`, `nothing_due`,
`presented`, `complete`, `error`).

**Contract**: `export default function SittingOverlay(): JSX.Element` — a single component;
internal helpers are not exported (no other file imports them).

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm typecheck`

---

## Phase 6: Sitting overlay — happy path behaviour

### Overview

Render and drive the normal flow: loading, front, toggle, both grading input paths, advancing.

### Changes Required:

#### 1. Fill the happy-path rendering and input handling

**File**: `tui/src/screens/SittingOverlay.tsx`

**Intent**: On mount, call `useSittingStore.getState().open()` (same `useEffect`-on-mount
pattern as `CaptureScreen`'s `initSession`). Render a loading indicator during `opening`
(text, per `NoteListOverlay`'s `"Loading..."` precedent), then the front, then the back when
`isBackVisible`. `useInput` wires `t` to `toggleBack()`, digit keys `1`-`4` to
`submitGrade()` directly, and up/down arrows to `moveSelection()` with Enter calling
`submitGrade()` with the highlighted grade — active regardless of `isBackVisible`.

**Contract**: No new exported symbols.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm vitest run test/sittingOverlay.test.tsx`
- `cd tui && pnpm test`

---

## Phase 7: Sitting overlay — terminal and error states

### Overview

Render the three states outside the grade loop: nothing due, complete, and error-with-retry.

### Changes Required:

#### 1. Fill the terminal-state rendering

**File**: `tui/src/screens/SittingOverlay.tsx`

**Intent**: `nothing_due` and `complete` each render a short message (ESC closes, same as
every other state — no extra affordance). `error` renders `{code, detail}` (per
`CaptureScreen`'s `StatusBar` precedent) plus a retry hint; a keypress (`r`) calls
`retry()`.

**Contract**: No new exported symbols.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm vitest run test/sittingOverlay.test.tsx`
- `cd tui && pnpm test`

---

## Phase 8: Wire `/remember` into the app shell

### Overview

Make the overlay reachable: the slash command, the absolute-overlay mount, and ESC handling.

### Changes Required:

#### 1. App-shell overlay flag

**File**: `tui/src/store/index.ts`

**Intent**: Add the shell-level open/close flag for this overlay, mirroring
`isNotesOverlayOpen`/`openNotes`/`closeNotes` — app-shell state stays out of the domain store.

**Contract**: `isSittingOverlayOpen: boolean`, `openSittingOverlay(): void`,
`closeSittingOverlay(): void` added to `AppState`/`AppActions`.

#### 2. `/remember` command

**File**: `tui/src/screens/CaptureScreen.tsx`

**Intent**: Typing `/remember` opens the overlay the same way `/notes` does today
(`CaptureScreen.tsx:63-66`).

**Contract**: A `REMEMBER_COMMAND = "/remember"` constant checked in `handleSubmit` alongside
`NOTES_COMMAND`; also added to the `focus` gate on the `TextInput` (`CaptureScreen.tsx:103`)
so typing is disabled while this overlay is open, matching the existing notes/streaming gates.

#### 3. Mount the overlay and close it on ESC

**File**: `tui/src/app.tsx`

**Intent**: Stack `SittingOverlay` the same absolute-position way as `NoteListOverlay`
(`app.tsx:42-65`); ESC closes it and resets its domain state, same branch order as the
existing detail/notes checks (`app.tsx:24-37`).

**Contract**: `useInput` gains a branch calling `closeSittingOverlay()` and
`useSittingStore.getState().reset()` when `isSittingOverlayOpen` is true; the render tree gains
a third absolute-positioned conditional block alongside the existing notes/detail one.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm vitest run test/app.test.tsx`
- `cd tui && pnpm test`
- `cd tui && pnpm typecheck`
- `cd tui && pnpm lint`

#### Manual Verification:
- `cd backend && uv run fastapi dev src/main.py`, then run the TUI, type `/remember`, and work
  through a full sitting: front shown, `t` toggles the back on and off, grade with a number key,
  grade the next card with arrows + Enter, reach completion (or nothing-due on an empty
  backlog), and confirm ESC closes the overlay from every state.

---

## Testing Strategy

### Unit Tests:
- `tui/test/sittings.test.ts` (Phase 2) — mocked-`fetch` request/response mapping and the
  `SittingHttpError` path, per `test/cards.test.ts`'s convention.
- `tui/test/sittingStore.test.ts` (Phase 4) — every state-machine transition, including retry
  re-issuing the exact failed action.
- `tui/test/sittingOverlay.test.tsx` (Phases 6-7) — rendering and `useInput` behaviour via
  `ink-testing-library`, per `test/noteListOverlay.test.tsx`'s convention.

### Integration Tests:
- `tui/test/app.test.tsx` (Phase 8) — `/remember` opening the overlay and ESC closing it,
  extending the existing `/notes` coverage in the same file.

### Manual Testing Steps:
- Phase 8's Manual Verification above is the only manual check; every other phase is fully
  covered by automated tests.

## Performance Considerations

None beyond what the backend already bounds — one card presented at a time, no polling.

## Migration Notes

None — this is new, additive surface; no existing TUI state or file is removed.

## References

- Frame: `context/changes/remember-flow-review-session-tui/frame.md`
- Backend routes: `backend/src/adapters/http/remember.py`
- Backend DTOs: `backend/src/application/remember/dto.py`
- Backend plan (origin surface): `context/changes/remember-flow-review-session/plan-brief.md`
- `/notes` overlay precedent: `tui/src/screens/NoteListOverlay.tsx`, `tui/src/app.tsx`
- Structured HTTP error precedent: `tui/src/api/stream.ts:63-71`, `tui/src/store/chat.ts`
- Execution state: `todos.md`
