# Implementation review r1

change-id: remember-flow-review-session-tui
scope: full
date: 2026-09-10
reviewed at 760a4ed

## Verdicts

| Dimension | Verdict |
| --- | --- |
| Plan Adherence | FAIL |
| Scope Discipline | PASS |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | PASS |

**Overall: NEEDS ATTENTION**

## Findings

### R1-F1 — OpenAPI schema never picked up review-sitting routes

- **Severity:** WARNING
- **Dimension:** Plan Adherence (MISSING)
- **Location:** `context/changes/remember-flow-review-session-tui/plan.md` Phase 1 § Regenerate the OpenAPI schema
- **Evidence:** proof-test — `tui/test/implReviewR1F1_schemaPaths.test.ts` fails at reviewed HEAD because `tui/src/api/generated/schema.d.ts` contains no `"/review-sittings"` path keys (vitest output: expected schema to contain `"/review-sittings"`).
- **Fix:** Regenerate `tui/src/api/generated/schema.d.ts` with `cd tui && pnpm generate:api` against a running backend that exposes the three review-sitting routes; do not hand-edit the generated file.

### R1-F2 — Sitting API bypasses the shared openapi-typed client

- **Severity:** WARNING
- **Dimension:** Pattern Consistency
- **Location:** `tui/src/api/sittings.ts:39-40`
- **Evidence:** citation — sibling modules use the generated client (`import { client } from "./client.js"` in `tui/src/api/cards.ts:1` and `tui/src/api/notes.ts:1`), while `sittings.ts` implements `requestJson` with raw `fetch(url, init)` (`const response = await fetch(url, init);`). Plan Phase 1 Intent: "matching how `api/cards.ts` and `api/notes.ts` already work."
- **Fix:** Route sitting HTTP calls through `client` and the regenerated OpenAPI path types, keeping camelCase DTO mapping at the module boundary like `cards.ts` and `notes.ts`.

## Retractions

(none)
