# Implementation review r3

change-id: remember-flow-source-jump
scope: full
date: 2026-09-11
reviewed at ad6fb35

## Verdicts

| Dimension | Verdict |
| --- | --- |
| Plan Adherence | WARNING |
| Scope Discipline | WARNING |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | FAIL |

**Overall: NEEDS ATTENTION**

## Findings

### R3-F1 — Phase 11 Automated Verification command collects no tests

- **Severity:** WARNING
- **Dimension:** Success Criteria
- **Location:** `plan.md` Phase 11 Success Criteria
- **Evidence:** command-output — `cd backend && uv run pytest tests/features -q` exits `5` with stdout `no tests ran in 0.16s`. Gherkin scenarios under `backend/tests/features/` load only via `backend/tests/bdd/test_features.py` (`pytest_bdd.scenarios`); the same US-10/US-11 scenarios pass when invoked as `cd backend && uv run pytest tests/bdd/test_features.py -q -m remember-flow` (exit `0`, 32 passed).
- **Fix:** Either make `tests/features` a collectable pytest entrypoint (as the plan documents) or change Phase 11's Automated Verification bullet to the bdd loader path so CI and humans can run the documented command without a silent no-op.

### R3-F2 — Card source probe state lives in the sitting store, not overlay-local state

- **Severity:** WARNING
- **Dimension:** Plan Adherence (DRIFT)
- **Location:** `tui/src/store/sitting.ts:44-45`, `plan.md` Phase 8
- **Evidence:** citation — Phase 8 Contract: *"Local state `sourceView: { source: CardSource; isExpanded: boolean; offset: number } | null` and `isSourceAvailable: boolean`"* (`plan.md:570-573`). Implementation keeps fetched source data in zustand: `cardSource: CardSource | null` and `isCardSourceProbeComplete: boolean` (`tui/src/store/sitting.ts:44-45`), while `SittingOverlay.tsx` only holds `sourceView` offset/expansion (`SittingOverlay.tsx:58`). Automated tests still assert once-per-reveal fetch behavior.
- **Fix:** Align the plan's Phase 8/9 Contracts with the store-owned probe fields, or move availability and cached `CardSource` back into `SittingOverlay` local state as originally specified.

### R3-F3 — `cardSourceProbe.ts` is outside every phase's Changes Required

- **Severity:** WARNING
- **Dimension:** Scope Discipline
- **Location:** `tui/src/lib/cardSourceProbe.ts:1-22`
- **Evidence:** citation — No phase lists `tui/src/lib/cardSourceProbe.ts` under Changes Required; Phase 9 names only `SittingOverlay.tsx` and `DueOverlayFooter.tsx` (`plan.md:605-607`). The module deduplicates in-flight `fetchCardSource` calls (`cardSourceProbe.ts:4-21`) and is imported from `tui/src/store/sitting.ts:13`.
- **Fix:** Name `cardSourceProbe.ts` explicitly in the phase Contract that introduces in-flight deduplication, or fold the helper into a file already listed in Changes Required.

## Retractions

(none)
