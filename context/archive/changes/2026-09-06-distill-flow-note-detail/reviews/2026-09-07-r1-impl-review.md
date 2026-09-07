# Implementation Review r1 — distill-flow-note-detail

reviewed at a8dc6b6

change-id: distill-flow-note-detail
scope: full
date: 2026-09-07

## Verdicts

| Dimension | Verdict |
| --- | --- |
| Plan Adherence | WARNING |
| Scope Discipline | WARNING |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | PASS |

**Overall: NEEDS ATTENTION** — three WARNING dimensions.

## Findings

### R1-F1 — WARNING — Scope Discipline

**Location:** `tui/src/screens/CaptureScreen.tsx:103`

**Evidence:** citation — `focus={!isStreaming && !isNotesOverlayOpen}`, added in commit `a8dc6b6` (message carries `distill-flow-note-detail`, not recorded on any `todos.md` row). No phase's Changes Required across Phases 1–11 names `CaptureScreen.tsx`. `plan.md`'s Current State Analysis (bullet on pre-existing polish) states: "Uncommitted, pre-existing polish to `NoteListOverlay.tsx`/`app.tsx`/`CaptureScreen.tsx` (... capture input disabled while the overlay is open) is already in the working tree from an earlier, uncommitted session on S-03. This plan builds on that state as given — it is not part of this change's phases." At plan-write time (`201fbb5`) `CaptureScreen.tsx`'s `focus` prop read `focus={!isStreaming}` only — the `!isNotesOverlayOpen` clause postdates the plan and was added outside any phase's Changes Required.

**Fix:** `CaptureScreen.tsx` stays out of this change's diff; overlay-aware focus gating belongs in a phase's own Changes Required (this change or a follow-up), not a same-day polish commit riding under this change-id.

### R1-F2 — WARNING — Plan Adherence (DRIFT)

**Location:** `tui/src/screens/NoteDetailScreen.tsx:16-18`

**Evidence:** proof-test — `refetches when mounted with a selectedNoteId that already matches a cached note` (`tui/test/noteDetailScreen.test.tsx`), run at `a8dc6b6`: **red** — `Timed out waiting for condition` (`getNote` never called). `proof-test skipped: HEAD on default branch` — no evidence commit; the test is left in the working tree, unstaged.

Phase 10 Contract (§1 Fetch on open): `useEffect(() => { if (selectedNoteId !== null) void useNoteDetailStore.getState().fetchNote(selectedNoteId); }, [selectedNoteId])` — fetch is unconditional whenever `selectedNoteId` is non-null. The actual code (commit `de7080d9`, Phase 10's own behavior commit) adds an early return: `if (note?.noteId === selectedNoteId) { return; }`, skipping the fetch whenever the store already holds a note with a matching id.

**Fix:** opening a note must not depend on whatever the store happens to already hold; either restore the contract's unconditional fetch, or have `plan.md` state the caching intent explicitly so a stale note (edited server-side since last viewed) can't be shown without a fresh fetch.

### R1-F3 — WARNING — Pattern Consistency

**Location:** `tui/src/screens/NoteListOverlay.tsx:10`

**Evidence:** citation — `function clamp(value: number, min: number, max: number): number {` at line 10, declared *before* the file's public `export default function NoteListOverlay()` at line 14 (added in `0309166d`, Phase 11's own commit). Two sibling files agree on the opposite ordering: `tui/src/screens/CaptureScreen.tsx:17` (`export default function CaptureScreen()`) precedes its first private helper (`UserLabel`, line 111); `tui/src/api/stream.ts` — all public exports (lines 10-102) precede its only private helper `parseStreamEvent` (line 186). `context/foundation/rules/code-ordering.md`: "Within a file, the public interface comes first; private/internal helpers come last."

**Fix:** move `clamp` below `NoteListOverlay`'s default export, alongside the file's other private helpers (`NoteRow`, `StatusBadge`, `formatElapsed`).

### R1-F4 — OBSERVATION — Plan Adherence (DRIFT)

**Location:** `tui/src/screens/NoteDetailScreen.tsx:27-34`, `tui/src/screens/NoteListOverlay.tsx:52-60`

**Evidence:** citation — Phase 10 Contract specifies tag rendering as `{note.tags.length > 0 && (<Text dimColor>{note.tags.map((t) => t.label).join(" · ")}</Text>)}`. The actual code (added in `a8dc6b6`) wraps this in an outer `<Text>` with a `<Text dimColor>Tags: </Text>` label prefix, and adds `marginTop`/`gap` layout to both `NoteDetailScreen.tsx` and `NoteListOverlay.tsx` not named in either Phase 10's or Phase 11's Contract. Cosmetic only — `tui/test/noteDetailScreen.test.tsx` was extended in the same commit and the Phase 10/11 Success Criteria commands still pass (see Success Criteria verdict).

**Fix:** none required — recorded so a future review doesn't re-derive the same diff as new drift.

## Retractions

None — no green proof-tests this run.
