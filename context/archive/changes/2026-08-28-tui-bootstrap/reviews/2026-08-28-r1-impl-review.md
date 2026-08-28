# Implementation Review r1

reviewed at 986269c

change-id: tui-bootstrap
scope: full
date: 2026-08-28

## Verdicts

| Dimension | Verdict |
| --- | --- |
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | FAIL |

**Overall: NEEDS ATTENTION**

## Findings

### R1-F1 — `pnpm --filter tui typecheck` exits non-zero

- **Severity:** WARNING
- **Dimension:** Success Criteria
- **Location:** `tui/test/app.test.tsx:3`
- **Evidence:** command-output — `pnpm --filter tui typecheck` exited 2:

  ```
  test/app.test.tsx(3,17): error TS5097: An import path can only end with a '.tsx' extension when 'allowImportingTsExtensions' is enabled.
  ```

  Phase 2 and Phase 3 Automated Verification both require `pnpm --filter tui typecheck` exits 0; typecheck passed before the Phase 4 test file landed (`33f5cc7` exit 0, `353c17d` exit 2). The regression traces to `import App from "../src/app.tsx";` introduced in `77706a2`.
- **Fix:** Test imports must resolve under `tsc --noEmit` without enabling `allowImportingTsExtensions`; `pnpm --filter tui typecheck` must exit 0 as required by Phase 2 and Phase 3 automated verification.

### R1-O1 — `pnpm-workspace.yaml` carries undeclared `allowBuilds`

- **Severity:** OBSERVATION
- **Dimension:** Scope Discipline
- **Location:** `pnpm-workspace.yaml:4-5`
- **Evidence:** citation — Plan Phase 1 workspace contract specifies only `packages: ["tui"]`; the committed file also declares `allowBuilds:\n  esbuild: true`, which is benign scaffolding for esbuild native builds but outside the stated contract.
- **Fix:** N/A (artifact-only observation).

### R1-O2 — Extra bootstrap frame assertion beyond plan contract

- **Severity:** OBSERVATION
- **Dimension:** Scope Discipline
- **Location:** `tui/test/app.test.tsx:12-16`
- **Evidence:** citation — Plan Phase 4 Automated Verification names a single test asserting `App` renders `"Weles TUI — bootstrap OK"` via `lastFrame()`; `it("renders a non-empty bootstrap frame", …)` is additional coverage with no plan requirement.
- **Fix:** N/A (artifact-only observation).

## Retractions

None.
