# Implementation Review r1 — distill-flow-note-cards

reviewed at 23f0036

change-id: distill-flow-note-cards
scope: full
date: 2026-09-08

## Verdicts

| Dimension | Verdict |
| --- | --- |
| Plan Adherence | WARNING |
| Scope Discipline | PASS |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | PASS |

**Overall: APPROVED** — two WARNING dimensions, no FAIL.

Success Criteria commands at `23f0036`: `cd backend && uv run pytest tests/integration/test_notes_http.py -v` — 8 passed; `cd backend && uv run pytest` — 273 passed; `cd backend && uv run ruff check src` — all checks passed; `cd backend && uv run basedpyright` — 0 errors/0 warnings/0 notes; `cd tui && npm run build` — success. `cd tui && npm test` — implementation suites green; the R1-F1 proof-test added by this review is red by design.

## Findings

### R1-F1 — WARNING — Plan Adherence (DRIFT)

**Location:** `tui/src/screens/CardListScreen.tsx:26-36`

**Evidence:** proof-test — `does not keep another note's cards visible while the new note's cards load` (`tui/test/cardListScreen.test.tsx`), run at `23f0036`: **red** — `expected 'Note …Cards… 1 card…' not to contain 'Leftover front from another note'`. Evidence commit `17a8cd4`.

Phase 6 Contract (§2 Card list behavior): "Fetches through `useCardsStore.fetchCards(selectedNoteId)` in a mount `useEffect`, as `NoteDetailScreen` does." `fetchCards` resets `{ cards: [], isLoading: true }`. The actual code (commit `739ebc3a`, Phase 6's own behavior commit) branches: if `store.cards.length === 0` it calls `fetchCards`, otherwise `refresh()`, which "re-runs the fetch for the currently selected note id without clearing the visible list" (Phase 4 Contract). `openDetail` / `closeDetail` do not clear `useCardsStore`, so opening note B's cards tab after viewing note A keeps A's cards on screen until B's `refresh` settles.

**Fix:** opening the cards tab must not display cards that belong to a previously opened note; mount must go through `fetchCards`, which clears the list, rather than `refresh`.

### R1-F2 — OBSERVATION — Pattern Consistency

**Location:** `tui/src/screens/CardListScreen.tsx:71-72`

**Evidence:** citation — `{isLoading && cards.length === 0 && <Text>Loading...</Text>}` immediately followed by `{cards.length === 0 && <Text>No cards for this note</Text>}`. Two siblings gate empty/body behind loading: `tui/src/screens/NoteDetailScreen.tsx:35-36` (`{isLoading && note === null && <Text>Loading...</Text>}` then `{note !== null && (`); `tui/src/screens/NoteListOverlay.tsx:51` (`{items.length === 0 && isLoading && <Text>Loading...</Text>}` — no empty-state line while loading). Initial `fetchCards` sets `cards: []` + `isLoading: true`, so both "Loading..." and "No cards for this note" render together.

**Fix:** the empty-list line is for a settled empty result, not for the in-flight fetch; do not show "No cards for this note" while `isLoading` is true.

### R1-F3 — OBSERVATION — Pattern Consistency

**Location:** `tui/src/store/cards.ts:16-23`

**Evidence:** citation — `function surfaceCardsError(error: unknown) {` at line 16, declared before the file's public `export const useCardsStore` at line 23. Two siblings agree on public-before-private: `tui/src/screens/NoteListOverlay.tsx:10` (`export default function NoteListOverlay()`) precedes `clamp` at line 67; `tui/src/api/stream.ts` — public exports (from line 10) precede its private helper `parseStreamEvent` at line 186. `context/foundation/rules/code-ordering.md`: "Within a file, the public interface comes first; private/internal helpers come last."

**Fix:** move `surfaceCardsError` below `useCardsStore`, alongside the file's public interface-first ordering.

## Retractions

None — no green proof-tests this run.
