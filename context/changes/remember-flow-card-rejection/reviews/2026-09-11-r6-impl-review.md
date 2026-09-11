# Implementation review r6

- **change-id**: remember-flow-card-rejection
- **scope**: full
- **date**: 2026-09-11
- **reviewed at** 5527a90

Phases 8, 9 and 10 are started and had no prior implementation review; the invocation
asked for them specifically, so they carry this pass. Phases 1 through 7 were reviewed at
`r5` (`9fd0796`) and are revisited here only for dedup — see the last section.

## Verdicts

| Dimension | Verdict |
| --- | --- |
| Plan Adherence | PASS |
| Scope Discipline | WARNING |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | PASS |

**Overall: APPROVED** — two WARNING dimensions, no FAIL, no CRITICAL.

### Notes on the PASS verdicts

- **Plan Adherence** — every Contract in phases 8, 9 and 10 is on disk. `rejectCard`
  checks `response.status === 204` **before** the `if (error || !data)` guard
  (`tui/src/api/sittings.ts:156-161`), exactly as phase 8's Contract requires;
  `currentCard` maps all five documented fields with `due` through `toDuePartition`
  (`sittings.ts:173-180`); `rejectCurrentCard` shares `submitGrade`'s `isSubmitting`
  guard and reuses its completion tail (`store/sitting.ts:278-341` against `215-277`);
  `LastAction` gained `{ type: "reject" }` and `retry()` dispatches it
  (`store/sitting.ts:25`, `351-352`); the `x` binding sits after the
  `phase !== "presented"` early return and is gated on `isBackVisible`
  (`screens/SittingOverlay.tsx:54-66`); `REJECT_HINT` renders only alongside the back
  (`SittingOverlay.tsx:121`); the generated schema carries both new paths
  (`grep -n "current-card\|rejection" tui/src/api/generated/schema.d.ts` → lines 160 and
  211) and is pinned by `tui/test/implReviewR1F1_schemaPaths.test.ts:16-18`. All six
  `vi.mock` factories named by phase 8's Contract list `rejectCard` and `currentCard`.
  Phase 10 added no production code — the gate and the hint landed whole in phase 8's
  commit `3c55912`, which is what phase 8's own Contract #4 asked for, so this is not
  drift.
- **Architecture** — no boundary moved. The new exports join the existing
  `src/api/sittings.ts` module, the store action sits beside `submitGrade`, and the
  overlay still reaches the API only through the store. `DueOverlayFooter` gained props
  rather than a store subscription, keeping it presentational like its siblings.
- **Pattern Consistency** — no candidate survived the gate. `rejectCurrentCard`'s shape,
  error funnel and `sittingHttpErrorState` reuse match `submitGrade` line for line; the
  evidence test naming follows `test/duePollClobbersGrade.test.ts`. The one candidate
  considered and dropped: `test/app.test.tsx:72` also mocks `src/api/sittings` and stubs
  only `openSitting`, so `rejectCard` and `currentCard` are unstubbed there — but
  `gradeCard` and `revealBack` were already unstubbed in that factory before this change,
  so the file's narrow stub set is its established design, not a hole this change opened.
  No sibling disagreement to cite.
- **Success Criteria** — every Automated Verification command on phases 8, 9 and 10 was
  run at `5527a90` and exited 0. See `R6-F0` below.

## Findings

### R6-F1

- **Id**: `R6-F1`
- **Severity**: WARNING
- **Dimension**: Safety & Quality (reliability)
- **Location**: `tui/src/store/sitting.ts:351-352`
- **Evidence:** `proof-test`

  Test: `tui/test/rejectRetryReissuesRejection.test.ts`, run at `5527a90` — **red**:

  ```
  FAIL  test/rejectRetryReissuesRejection.test.ts > rejection retry >
    does not call rejectCard again when the rejection succeeded and only the re-read failed
  AssertionError: expected "spy" to be called 1 times, but got 2 times
   ❯ test/rejectRetryReissuesRejection.test.ts:77:24
  ```

  `rejectCurrentCard` performs two sequential server calls inside one action
  (`store/sitting.ts:294-295`):

  ```ts
  await rejectCard(sittingId, cardId);
  const result = await currentCard(sittingId);
  ```

  When the first succeeds and the second fails with any code other than
  `sitting_expired`, the catch drops the store into `phase: "error"` with
  `lastAction: { type: "reject" }` still set. The overlay's error branch offers exactly one
  key — `r` → `retry()` (`screens/SittingOverlay.tsx:47-52`) — and `retry()` replays the
  whole action, re-issuing `rejectCard` for a card the backend has already settled. The
  second call cannot succeed: `RejectCardCommand.handle` runs
  `sitting.guard_outcome(card_id, present, sitting_events, reviewed_at)`
  (`backend/src/application/remember/commands/reject_card.py:30`), and the card is no
  longer offered once its rejection is in the event log, so the command raises and the
  store lands back in `error`. The user is pinned in an error screen whose only advertised
  recovery re-creates it; ESC out of the sitting is the sole exit. The test's first two
  assertions — `phase === "error"` and `rejectCard` called once — pass, so the red is the
  claimed defect and nothing else. `submitGrade` does not share this shape: it makes one
  call, so replaying it is idempotent from the client's point of view.

- **Fix:** A retry must not replay a step whose server write already committed. Once
  `rejectCard` has resolved, the outstanding work is the re-read alone — `retry()` (or the
  action it dispatches) must resume from `currentCard`, not from the rejection. Encode
  which leg is still owed in `lastAction`, or recover the presented card without going
  through `rejectCurrentCard`; do not widen the error branch's key set instead.

### R6-F2

- **Id**: `R6-F2`
- **Severity**: OBSERVATION
- **Dimension**: Scope Discipline
- **Location**: `tui/src/components/DueOverlayFooter.tsx:17-18`
- **Evidence:** `citation`

  `tui/src/components/DueOverlayFooter.tsx:17-18` is in phase 8's diff (`3c55912`, +9
  lines):

  ```tsx
  showRejectHint?: boolean;
  rejectHint?: string;
  ```

  No phase's Changes Required names this file. Phase 8 lists five **File** entries —
  `tui/src/api/generated/schema.d.ts`, `tui/src/api/sittings.ts`, `tui/src/store/sitting.ts`,
  `tui/src/screens/SittingOverlay.tsx` and the six test modules — and `DueOverlayFooter`
  appears only inside Contract prose, at `plan.md:618`: "New module const `REJECT_HINT`,
  passed to `DueOverlayFooter` alongside `TOGGLE_CARD_HINT`." Passing a new prop to a
  component whose props are a closed type necessarily edits that component, so the path is
  implied but never accounted for.

  Benign: both props are optional with `showRejectHint = false` defaulting, so the
  component's other behaviour and its single existing call site are untouched, and nothing
  in What We're NOT Doing is violated. Recorded, not queued. This is the same shape as
  `R5-F2` — a phase Contract naming a collaborator it does not list as a File.

- **Fix:** When a Contract passes a new prop to an existing component, that component's
  path belongs in the phase's Changes Required as its own File entry; prose mentioning the
  component is not an entry.

### R6-F0 — Success Criteria command output

Not a finding; recorded because the dimension's evidence kind is `command-output` and every
reviewed phase's Automated Verification was run at `5527a90`.

- Phase 8, phase 10 — `cd tui && pnpm test` → `Test Files 30 passed (30)`,
  `Tests 180 passed (180)`, exit 0.
- Phase 8 — `cd tui && pnpm build` → `ESM dist/cli.js 59.60 KB`, `Build success in 29ms`,
  exit 0.
- Phase 9 — `cd tui && pnpm vitest run test/sittings.test.ts` and
  `test/sittingStore.test.ts`; phase 10 — `test/sittingOverlay.test.tsx`. Run together:
  `Test Files 3 passed (3)`, `Tests 45 passed (45)`, exit 0.

The evidence test `tui/test/rejectRetryReissuesRejection.test.ts` was committed after these
runs, so `pnpm test` is red at `2e4a84e` by exactly one test until `R6-F1` is fixed.

## Retractions

(none — the one `proof-test` this review wrote came back red, so no claim was retracted.)

## Dedup against predecessors

- `r1` (phase 2 property), `r2` (`R2-F1`–`R2-F4`, phase 2 mutation), `r3` (phase 4
  mutation), `r4` (`R4-F1`, phase 6 mutation) — all closed or killed at `r5`; nothing
  re-raised here, and none of them touch the TUI.
- `r5` (`R5-F1`, `R5-F2`) — `R5-F1` closed as todos row `4.5` at `ca10e39`;
  `backend/src/domain/remember/outbox.py` now hands the dump through unmodified. `R5-F2`
  stayed an OBSERVATION and queued no row; `R6-F2` is the same *shape* in a different file
  and a different phase, so it takes its own id rather than being noted against `R5-F2`.
- No prior artifact recorded a retraction, so nothing was carried forward.
