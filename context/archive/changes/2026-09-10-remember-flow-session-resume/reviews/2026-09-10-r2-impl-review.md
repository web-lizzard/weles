# Impl review — full plan

reviewed at 8505736

- **change-id**: remember-flow-session-resume
- **scope**: full
- **date**: 2026-09-10
- **phases reviewed**: 1–10 (every phase is started)
- **moving tree**: the review began at `d11b291` with `tui/src/api/sittings.ts` and
  `tui/src/screens/SittingOverlay.tsx` uncommitted, and `SittingOverlay.tsx` was edited again
  mid-review (the resumed marker became a banner, `RESUMED_BANNER`). Phase 10 then committed both
  as `8505736`, which is the reviewed-at SHA above. Every finding was re-verified against that
  state; no finding rests on the earlier working-tree content.

## Verdicts

| Dimension | Verdict |
| --- | --- |
| Plan Adherence | WARNING |
| Scope Discipline | PASS |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | FAIL |

**Overall: NEEDS ATTENTION** — one non-CRITICAL FAIL (Success Criteria).

### How the verdicts were reached

- **Plan Adherence** — the backend contracts land verbatim: the convergent branch in
  `open_sitting.py:52-67` returns `SittingResumedDTO` without a save, `due_card_ids` replaced
  the inline comprehension, `_guard_grade` checks `is_offered` first, and both read handlers
  refuse an expired sitting immediately after the not-found check. Two DRIFTs survive
  (`R2-F1`, `R2-F4`); neither is MISSING and neither is major, so this is WARNING not FAIL.
- **Scope Discipline** — the implementation diff (`412f65a..HEAD` plus working tree) touches
  only paths named in Changes Required, apart from `tui/test/app.test.tsx` (+3) and
  `tui/test/implReviewR2F4_submitGradeRace.test.ts` (+2), both of which only widen fixtures to
  the new store/DTO shape — exactly what Phase 8's own Success Criteria anticipated. No
  `What We're NOT Doing` entry is violated: no `expires_at` on any DTO, no URL change, no close
  command, no due-count query, no SQL adapter.
- **Safety & Quality** — no surviving finding. The expiry-recovery loop guard holds:
  `open()`'s catch (`store/sitting.ts:139-145`) deliberately has no `SITTING_EXPIRED` branch, so
  a `sitting_expired` from the recovery open falls through to the ordinary error path, and
  `retry()` still re-issues `open()` because `open()` sets `lastAction` before awaiting.
- **Architecture** — no surviving finding. Query handlers still take no `UnitOfWork`;
  `card_is_due` stayed in the domain.
- **Pattern Consistency** — one surviving finding (`R2-F2`).
- **Success Criteria** — every command in every reviewed phase was run. All pass except
  `cd backend && uv run pyright`, which exits non-zero because the binary does not exist
  (`R2-F3`). The pack's rule keys this dimension's verdict on the exit code, not on the finding's
  severity, so the dimension stays FAIL even though `R2-F3` was downgraded to OBSERVATION at the
  author's direction and queues no row. The substantive type check is clean.

### Commands run

| Command | Result |
| --- | --- |
| `cd backend && uv run pytest` | exit 0 — 401 passed |
| `cd backend && uv run pytest tests/bdd -m "remember-flow"` | exit 0 — 24 passed, 25 deselected |
| `cd backend && grep -rn "card_is_due" src/application` | exit 1 — no hits, as the plan requires |
| `cd backend && uv run pyright` | non-zero — `error: Failed to spawn: pyright` (see `R2-F3`) |
| `cd backend && uv run basedpyright` | 0 errors, 0 warnings, 0 notes |
| `cd tui && pnpm test` | exit 0 — 25 files, 149 tests passed |
| `cd tui && pnpm typecheck` | exit 0 |
| `cd tui && pnpm lint` | exit 0 — 1 pre-existing warning in `test/appNotesFetchIsolation.test.tsx`, outside this diff |

## Findings

### R2-F1 — the outstanding count is shown only while a card is presented

- **Severity**: WARNING
- **Dimension**: Plan Adherence — DRIFT (behavioral)
- **Location**: `tui/src/screens/SittingOverlay.tsx:101-107`
- **Evidence** (`proof-test`): `tui/test/implReviewR2F1_outstandingCountFooter.test.tsx`, both
  cases red at `d11b291`.
  - *"still reports how many cards are left when a grade fails and the live sitting is shown as
    an error"* — `expected '← ESC to go back\n\n…\nPress r to retry.' to match /3 left/i`, with
    `sittingId` asserted still non-null.
  - *"reports zero cards left once the sitting it still holds is complete"* —
    `expected '← ESC to go back\n\nSitting complete' to match /0 left/i`, with `sittingId`
    asserted still non-null.

  The plan's Phase 10 Contract (`plan.md:615-617`) reads: *"The footer carries the outstanding
  count in every phase that has a sitting, alongside the existing `TOGGLE_CARD_HINT`."* The
  implementation gates the whole footer on `phase === "presented"`, so the two other phases that
  hold a live `sittingId` — `complete` and `error` — render no count. Phase 10's own tests
  (`test/sittingOverlay.test.tsx:318-354`) assert the count only in `presented`, which is why the
  gap survived the phase green. The `8505736` rework moved the resumed marker into a banner and
  changed the margins, but left the footer's `phase === "presented"` gate untouched.
- **Fix:** the outstanding count must render whenever the store holds a `sittingId`, not only in
  the `presented` phase; the toggle hint may stay `presented`-only, because it is the hint, not
  the count, that is phase-specific.

### R2-F2 — the generated `outstanding_count` is cast optional and defaulted to zero

- **Severity**: WARNING
- **Dimension**: Pattern Consistency
- **Location**: `tui/src/api/sittings.ts:40-41`, `:75-77`, `:133-135`
- **Evidence** (`citation`):
  - `tui/src/api/sittings.ts:40` — `function readOutstandingCount(data: { outstanding_count?: number }): number {`
    and `:41` — `return data.outstanding_count ?? 0;`, reached through
    `:76` / `:134` — `data as { outstanding_count?: number },`.
  - `tui/src/api/generated/schema.d.ts:558` and `:583` (the `SittingOpenedDTO` and
    `SittingResumedDTO` bodies) and `:476` (`GradeAppliedDTO`) each declare
    `outstanding_count: number` — **required**, not optional. Phase 6 regenerated this file
    precisely so the field would be typed.
  - Sibling 1 — `tui/src/api/cards.ts:27-33`: `cardId: item.card_id, front: item.front,
    back: item.back, anchorQuote: item.anchor_quote,` — generated fields read straight off the
    typed payload, no cast, no default.
  - Sibling 2 — `tui/src/api/notes.ts:35-38,45-47`: `noteId: data.note_id, … content:
    data.content, … approvedAt: data.approved_at, createdAt: data.created_at,` — same. The only
    casts elsewhere in `src/api` (`sittings.ts:146`, `stream.ts:89,222`) are over `error` and raw
    stream payloads, which the generator leaves untyped; no sibling casts `data`.

  The cast widens a required field to optional and then substitutes `0`, so a backend that stops
  sending `outstanding_count` reports "0 left" instead of failing the build — the same silent-zero
  hole that `R1-F3` had to be killed by hand on the backend DTO.
- **Fix:** a field the generated schema declares required must be read directly off the typed
  payload; do not cast `data` to a looser shape or supply a fallback for it.

### R2-F3 — the plan's backend type-check command names a tool this project does not install

- **Severity**: OBSERVATION — downgraded from WARNING at the author's direction, to keep a
  plan-text correction out of the triage queue. The command's non-zero exit is unchanged, and so
  is the Success Criteria FAIL.
- **Dimension**: Success Criteria
- **Location**: `plan.md` Phases 2, 3, 4 and 5, Automated Verification
- **Evidence** (`command-output`): `cd backend && uv run pyright` →
  `error: Failed to spawn: 'pyright' / Caused by: No such file or directory (os error 2)`,
  non-zero exit. `backend/pyproject.toml:23` pins `basedpyright>=1.39.10` in the dev group and
  `[tool.basedpyright]` at `:68` configures it; `cd backend && uv run basedpyright` returns
  `0 errors, 0 warnings, 0 notes`. Four phases were therefore signed off against a criterion
  that cannot have been run as written.
- **Fix:** every Automated Verification command must name a binary this project installs; the
  backend type checker is `basedpyright`, and `uv run pyright` must not stand as a criterion.
  No triage row.

### R2-F4 — the acceptance feature file does not carry the name the plan gave it

- **Severity**: OBSERVATION
- **Dimension**: Plan Adherence — DRIFT (non-behavioral)
- **Location**: `plan.md:194`
- **Evidence** (`citation`): `plan.md:194` reads
  `**File**: `backend/tests/features/remember-flow/US-05-pick-up-where-you-left-off.feature``.
  On disk the file is `backend/tests/features/remember-flow/US-05-walking-away-costs-nothing.feature`.
  The implementation is the better one — `context/efforts/remember-flow/stories.md:51` titles
  US-05 *"Walking away costs nothing"*, and Phase 1's own Manual Verification asks that scenarios
  be drawn from `stories.md`. Recorded only so a future reader grepping `plan.md` for the path
  does not conclude the file is missing. No triage row.

## Retractions

None — both proof-tests written by this review are red.

Two claims were examined and dropped before the admissibility gate, recorded here so they are not
re-raised:

- *Retry is dead after a failed expiry recovery.* Not a defect: `recoverFromSittingExpired`
  (`store/sitting.ts:62-79`) clears `sittingId`/`cardId`, but the `open()` it awaits sets
  `lastAction: { type: "open" }` before its own await, so a subsequent `retry()` dispatches
  `open()` rather than the dead `submitGrade()` path.
- *The resume branch can dereference a missing card.* Not a defect: `assert card_id is not None`
  at `open_sitting.py:58` is reachable only when `is_finished` is false, which by
  `sitting.py:104-119` guarantees a non-empty eligible pool drawn from `present ⊆ by_id`.
