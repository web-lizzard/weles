reviewed at 645eb15

change-id: distill-flow-note-list
scope: full

## Verdicts

| Dimension | Verdict |
| --- | --- |
| Plan Adherence | PASS |
| Scope Discipline | WARNING |
| Safety & Quality | WARNING |
| Architecture | WARNING |
| Pattern Consistency | WARNING |
| Success Criteria | PASS |

**Overall: NEEDS ATTENTION** — four WARNING dimensions (more than two), no FAIL, no CRITICAL.

## Findings

### R1-F1 — WARNING

- **Dimension**: Architecture
- **Location**: `backend/src/domain/distill/note.py:25`
- **Evidence**: citation — `updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))`. Phase 1's Contract (`plan.md:68`) says only *"`Note` gains `updated_at: datetime`"* — no default — and Phase 1's Intent (`plan.md:66`) states *"Give `Note` a recency timestamp it alone controls."* The added `default_factory` lets any direct `Note(...)` construction silently receive a fresh `datetime.now(UTC)` instead of failing or matching `created_at`. It is already exercised, diverging from `created_at`, by `backend/tests/unit/distill/contracts/test_note_repository_contract.py:26-34`'s `_sample_note()`, which sets `created_at` explicitly but omits `updated_at` entirely.
- **Fix**: `Note.updated_at` must never gain a default outside `mint_note`'s explicit assignment — direct construction without going through `mint_note` should require the field, not silently default, so the aggregate stays the only path that ever sets it.

### R1-F2 — WARNING

- **Dimension**: Scope Discipline
- **Location**: `tui/src/api/client.ts:4-7`
- **Evidence**: citation — commit `e09e8d3` ("implement notes API client (p8)") changes the shared client to `export const client = createClient<paths>({ baseUrl: "http://localhost:8000", fetch: (...args) => globalThis.fetch(...args) });`. No phase's Changes Required names `tui/src/api/client.ts` (checked all 14 phases in `plan.md`). The change is real and load-bearing — `openapi-fetch`'s `createClient` captures `fetch: baseFetch = globalThis.fetch` once at import time, so `vi.stubGlobal("fetch", ...)` in `notes.test.ts` would not reach the shared client without this wrapper — but it silently touches a file also used by `stream.ts` (`startCaptureSession`, `approveNote`), outside any phase's stated scope. Benign (no "What We're NOT Doing" bullet is violated), hence WARNING not FAIL.
- **Fix**: shared TUI infrastructure (`api/client.ts`) touched to support a phase must be named in that phase's Changes Required — a mockability change to the shared client belongs in the plan, not riding silently along with an unrelated phase's commit.

### R1-F3 — WARNING

- **Dimension**: Pattern Consistency
- **Location**: `backend/src/adapters/out/in_memory/distill/list_notes_query.py:5`
- **Evidence**: citation (2 siblings) — `class InMemoryListNotesQuery:` drops the `Adapter` suffix both named sibling query adapters carry: `backend/src/adapters/out/in_memory/shared/outbox/envelope_query.py:4` (`class InMemoryOutboxEnvelopeQueryAdapter:`) and `backend/src/adapters/out/in_memory/capture/transcript_query.py:5` (`class InMemoryTranscriptQueryAdapter:`). `envelope_query.py` is the plan's own named precedent (`plan.md:31`) for this adapter's shape.
- **Fix**: in-memory query adapter classes in this codebase are named `InMemory<X>QueryAdapter`; `InMemoryListNotesQuery` should carry the same `...QueryAdapter` suffix as its two siblings.

### R1-F6 — WARNING

- **Dimension**: Safety & Quality
- **Location**: `tui/src/store/notes.ts:16,33-38`
- **Evidence**: proof-test — `tui/test/notesStorePolling.test.ts::"stopPolling clears every interval started, not only the most recent one"` (tagged `R1-F6` in-file). Red: `expected "spy" to be called 2 times, but got 7 times`. `pollIntervalId` is a single module-level variable; calling `startPolling` a second time before an intervening `stopPolling` overwrites it, orphaning the first `setInterval` forever — `stopPolling()` only ever clears the most recent one. proof-test skipped: HEAD on default branch (test written and run, left uncommitted in the working tree; no evidence commit, no proof SHA).
- **Fix**: `startPolling` must not leak a prior interval when called again before `stopPolling` — clear any existing interval at the top of `startPolling`, or otherwise make double-start impossible to orphan.

### R1-F7 — WARNING

- **Dimension**: Safety & Quality
- **Location**: `tui/test/app.test.tsx:82-140` (`describe("notes overlay dispatch", ...)`)
- **Evidence**: proof-test — `tui/test/appNotesFetchIsolation.test.tsx::"does not reach the real fetch boundary when the notes overlay mounts, under the same mocks app.test.tsx's notes-overlay tests use"` (tagged `R1-F7` in-file). Red: `expect(fetch).not.toHaveBeenCalled()` failed — `fetch` was called once with `url: "http://localhost:8000/notes"`. The `notes overlay dispatch` tests in `app.test.tsx` mock only `../src/api/stream`, never `../src/api/notes` or `../src/hooks/useNotesPolling`; dispatching `/notes` mounts the real `NoteListOverlay` → real `useNotesPolling` → real `listNotes()` → a real, unmocked `fetch` call. Two sibling test files establish the "isolate from the network" convention for this exact surface: `tui/test/notesStore.test.ts:6-12` mocks `../src/api/notes`, `tui/test/noteListOverlay.test.tsx:7-9` mocks `../src/hooks/useNotesPolling`. proof-test skipped: HEAD on default branch (test written and run, left uncommitted in the working tree; no evidence commit, no proof SHA).
- **Fix**: `app.test.tsx`'s notes-overlay tests must mock `../src/api/notes` (and/or `../src/hooks/useNotesPolling`), matching the isolation convention `notesStore.test.ts` and `noteListOverlay.test.tsx` already establish, so dispatching `/notes` never reaches a real `fetch`.

### R1-F4 — OBSERVATION

- **Dimension**: Pattern Consistency
- **Location**: `backend/src/application/distill/queries/list_notes.py:8-17`
- **Evidence**: citation (2 siblings) — `NoteListItemDTO` and `ListNotesQueryPort` are defined together in one module. Both named sibling query packages keep the DTO separate from the Protocol port: `backend/src/application/shared/outbox/queries/envelopes.py:3` imports `OutboxEnvelopeDTO` from `application.shared.outbox.dto`, and `backend/src/adapters/out/in_memory/shared/outbox/envelope_query.py:2` does the same. This is plan-directed, not implementation drift — Phase 3's Contract (`plan.md:120-130`) explicitly specifies the colocated shape — so it is not a defect in this change, only a codebase-convention note for whatever query this context adds next.
- **Fix**: query DTOs in this codebase live in their own module, separate from the Protocol port; the next query added to the `distill` context should restore that split rather than extend `list_notes.py`'s colocated shape.

### R1-F5 — OBSERVATION

- **Dimension**: Pattern Consistency
- **Location**: `tui/src/screens/CaptureScreen.tsx:63`
- **Evidence**: citation (2 siblings) — `useAppStore.getState().openNotes();` reads the store imperatively, while the same file's own sibling action (`approveDraft`, `CaptureScreen.tsx:21`: `useChatStore((state) => state.approveDraft)`) and the same diff's own `tui/src/app.tsx:8` (`useAppStore((state) => state.closeNotes)`) both use the hook-selector convention. This is plan-directed — Phase 12's Contract (`plan.md:492`) literally specifies `useAppStore.getState().openNotes()` — so it is not a defect in this change; functionally harmless since actions don't need reactive subscription.
- **Fix**: store actions dispatched from `CaptureScreen`'s `handleSubmit` should be read via the store's hook-selector convention (as `closeNotes` is in `app.tsx`), not `useAppStore.getState()`, to keep one dispatch idiom across the file.

## Retractions

None — no prior review exists for this change.
