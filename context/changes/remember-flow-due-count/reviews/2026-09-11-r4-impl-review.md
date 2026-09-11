# Implementation review r4

reviewed at d3f8d64

- **change-id**: remember-flow-due-count
- **scope**: full
- **phases reviewed**: 1–10 (every phase started)
- **evidence commit**: 2cbae57

## Verdicts

| Dimension | Verdict |
| --- | --- |
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | FAIL |

**Overall: NEEDS ATTENTION**

## Findings

### R4-F1 — a poll answering after a grade overwrites the fresher partition

- **Severity**: WARNING
- **Dimension**: Safety & Quality
- **Location**: `tui/src/store/due.ts:21-28`
- **Evidence**: `proof-test` — `tui/test/duePollClobbersGrade.test.ts`, red at d3f8d64.

  ```
  AssertionError: expected { total: 5, notYetSeen: 5, … } to deeply equal { total: 4, notYetSeen: 3, … }
  - Expected  + Received
      "notYetSeen": 3,   →   "notYetSeen": 5,
      "seenStillOwed": 1, →  "seenStillOwed": 0,
      "total": 4,        →   "total": 5,
  Test Files  1 failed (1) / Tests  1 failed (1)
  ```

  `fetchDue` writes its result unconditionally:

  ```ts
  const partition = await fetchDueCount();
  set({ partition, isStale: false });
  ```

  Nothing checks whether `applyPartition` ran while the request was outstanding. A poll
  issued before a grade, but answering after it, replaces the grade's partition with its
  own pre-grade reading, and the header and overlay carry that reading until the next
  tick — up to `DUE_POLL_INTERVAL_MS` (15 s).

- **Fix**: the store's partition must never move backwards in time — a `fetchDue`
  result may only be written when no newer partition has been applied since that request
  left. Order the writes; do not lengthen or shorten the poll interval to hide the window.

### R4-F2 — three phases verify with a checker this project does not install

- **Severity**: WARNING
- **Dimension**: Success Criteria
- **Location**: `plan.md`, Phase 1 / Phase 2 / Phase 3 Automated Verification
- **Evidence**: `command-output` — the plan's own bullet, run:

  ```
  $ cd backend && uv run pyright src tests
  error: Failed to spawn: `pyright`
    Caused by: No such file or directory (os error 2)
  exit 2
  ```

  The declared checker is `basedpyright` (`backend/pyproject.toml:23` —
  `"basedpyright>=1.39.10"`), which is also what the pre-commit hook runs. Under it the
  tree is clean:

  ```
  $ cd backend && uv run basedpyright src tests
  0 errors, 0 warnings, 0 notes
  ```

  Type checking therefore passes; the criterion as written can never be satisfied, and
  anyone re-running the plan's verification reads a false failure.

- **Fix**: a phase's Automated Verification bullet must name a command this repository can
  actually run. Correct the three bullets to the installed checker rather than adding a
  `pyright` shim or dependency to satisfy the prose.

## Observations

None.

## Retractions

None.

## Notes on what was checked and passed

- Backend `uv run pytest` — 426 passed. `tests/bdd` — 51 passed, US-07 green.
- `tests/unit/remember` (103), `test_due_count_query.py` (5),
  `test_remember_routes.py` (5) — all pass.
- `uv run python -c "from adapters.compose import get_due_count_query; get_due_count_query()"` — constructs.
- TUI `pnpm test` — 168 passed across 29 files; `pnpm typecheck` clean; `pnpm lint` exit 0
  (its one warning, unused imports in `tui/test/appNotesFetchIsolation.test.tsx:4-5`,
  blames to 6e21b79c, outside this change).
- Phase 9/10 geometry departs from those phases' Contract text — the header renders last
  and is hidden during review, overlays sit at `top={0} height={rows - 1}` — but `plan.md`'s
  own "Post-phase polish" block records that move, so it is not drift.
- `tui/src/components/DueOverlayFooter.tsx` and `tui/src/lib/dueFormat.ts` are outside
  Changes Required and likewise covered by that block. Remaining extras are test files.
- No path in the diff writes on a read: `DueCountQuery` takes no unit of work, and the
  route is a `GET`. "What We're NOT Doing" holds.
