# Implementation review r1

reviewed at 54fcb9f

change-id: auth-flow-instance-address
scope: full
date: 2026-09-13

## Verdicts

| Dimension | Verdict |
| --- | --- |
| Plan Adherence | PASS |
| Scope Discipline | WARNING |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | PASS |

**Overall: APPROVED**

## Findings

### R1-F1 — Sitting store edits outside Phase 4 Changes Required

- **Severity:** WARNING
- **Dimension:** Scope Discipline
- **Location:** `tui/src/store/sitting.ts:123-128`, `tui/src/store/sitting.ts:379-386`
- **Evidence:** `citation` — Phase 4 **Changes Required** lists `tui/src/api/instance.ts`, `tui/src/startup.ts`, API modules, and `tui/src/cli.tsx` only (`plan.md` lines 273-316); commit `b2a598e` also wraps `probeCurrentCardSource` in try/catch and maps non-HTTP grade errors to `phase: "error"` in `sitting.ts`, which is not named in that list.
- **Fix:** Keep instance-address work on the plan's listed paths; revert sitting-store behaviour changes here or track them under a change that owns sitting error UX.

## Retractions

*(none)*

## Automated verification (command-output)

Reviewed phases 1–4 automated commands were run from `tui/` on 2026-09-13; each exited 0.

- `pnpm typecheck` — exit 0
- `pnpm lint` — exit 0 (1 pre-existing unused-import warning in `test/appNotesFetchIsolation.test.tsx`)
- `pnpm vitest run test/instanceCommand.test.ts test/instanceAddress.test.ts` — 17 passed
- `pnpm vitest run test/instanceRouting.test.ts test/startup.test.ts` — 5 passed
- `pnpm test` — 223 passed

## Scope note

Diff scoped to commits whose messages carry `auth-flow-instance-address` (union todos SHAs): `tui/src/instance/*`, `tui/src/api/*` routing, `tui/src/startup.ts`, `tui/src/cli.tsx`, vitest setup, and change docs. No `localhost:8000` remains under `tui/src/`. Extra production path: `tui/src/store/sitting.ts` (see R1-F1).
