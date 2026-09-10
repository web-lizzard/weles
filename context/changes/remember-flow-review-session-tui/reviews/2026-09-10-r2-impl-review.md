# Implementation review r2

change-id: remember-flow-review-session-tui
scope: full
date: 2026-09-10
reviewed at ab287f4

## Verdicts

| Dimension | Verdict |
| --- | --- |
| Plan Adherence | FAIL |
| Scope Discipline | WARNING |
| Safety & Quality | WARNING |
| Architecture | WARNING |
| Pattern Consistency | WARNING |
| Success Criteria | PASS |

**Overall: NEEDS ATTENTION**

## Findings

### R2-F1 — `api/client.ts` modified outside any phase's Changes Required

- **Severity:** WARNING
- **Dimension:** Scope Discipline
- **Location:** `tui/src/api/client.ts:4-29`
- **Evidence:** citation — commit `043b0cd` (phase 2) adds a 24-line `delegatedFetch` function and rewires `createClient`'s `fetch` option to it (`tui/src/api/client.ts:27-29`: `export const client = createClient<paths>({ baseUrl: "http://localhost:8000", fetch: delegatedFetch });`). No phase's Changes Required lists `api/client.ts`; Phase 2's Contract reads "Same exported surface as Phase 1; no new symbols" and R2-F2's own plan-entry fix text (`plan.md` Phase 2 Review r1) says only "Route sitting HTTP calls through `client`," not "modify `client`."
- **Fix:** A fix that reaches into a shared, already-existing file outside the plan's Changes Required is out of scope for a phase whose Contract promises no new symbols; either amend the phase's Contract to name `client.ts` explicitly or land the shared-file change as its own reviewed step.

### R2-F2 — Untested cross-cutting change to the shared fetch delegate

- **Severity:** WARNING
- **Dimension:** Architecture
- **Location:** `tui/src/api/client.ts:4-25`
- **Evidence:** citation — `delegatedFetch` unwraps a `Request` instance into a plain `(url, init)` call (`tui/src/api/client.ts:8-23`), a behavior branch exercised implicitly by `tui/test/sittings.test.ts`'s fetch-shape assertions but with no test in the diff that exercises `client.ts` directly. `client.ts` backs every domain module (`api/cards.ts:1`, `api/notes.ts:1`, `api/stream.ts:6` each `import { client } from "./client.js"`), so a behavioral change here is cross-cutting infrastructure, not sitting-flow-local code.
- **Fix:** A change to `api/client.ts`'s fetch delegate needs its own direct test coverage (not only indirect coverage through one domain's request-shape assertions) before it ships, since every other domain module depends on the same function.

### R2-F3 — `openSitting` raises on the backend's own "just completed, no card" response

- **Severity:** WARNING
- **Dimension:** Plan Adherence (DRIFT)
- **Location:** `tui/src/api/sittings.ts:70-72`
- **Evidence:** proof-test — `tui/test/implReviewR2F3_openSittingCompleteNoCard.test.ts` fails at reviewed HEAD (`ab287f4`): `openSitting()` rejects with `Error: Incomplete opened sitting response` when the backend returns `{ kind: "opened", card_id: null, front: null, sitting_complete: true }`. Plan's Key Discoveries text: *"`application/remember/dto.py:13-18`'s `PresentedCardDTO` — and by extension `SittingOpenedDTO` — carries `card_id: UUID | None` and `front: str | None`, an in-flight fix … so a just-completed sitting reports `sitting_complete: true` with no card rather than raising. This plan treats that shape as given."* Current `backend/src/application/remember/dto.py` still types `SittingOpenedDTO` this way, so the shape is real and reachable.
- **Fix:** `openSitting` must treat a `kind: "opened"` response carrying `card_id: null`/`front: null` with `sitting_complete: true` as a normal, non-raising outcome — per the plan's own stated premise — not as an error condition.

### R2-F4 — `submitGrade` has no re-entrancy guard

- **Severity:** WARNING
- **Dimension:** Safety & Quality
- **Location:** `tui/src/store/sitting.ts:154-164`
- **Evidence:** proof-test — `tui/test/implReviewR2F4_submitGradeRace.test.ts` fails at reviewed HEAD (`ab287f4`): calling `submitGrade` twice before the first call's `gradeCard()` promise resolves issues `gradeCard` twice (expected once, got two). `isSubmitting` is set to `true` at `tui/src/store/sitting.ts:163` but is never read as a guard anywhere in `sitting.ts` or `SittingOverlay.tsx`'s `useInput` handler (`tui/src/screens/SittingOverlay.tsx:71-107` gates only on `phase === "presented"`).
- **Fix:** `submitGrade` (and the `useInput` dispatch that calls it) must treat `isSubmitting: true` as a guard against re-entry, not just a display flag, so the same card cannot be graded twice from one rapid double keypress.

### R2-F5 — Private helper declared before the public functions that use it

- **Severity:** WARNING
- **Dimension:** Pattern Consistency
- **Location:** `tui/src/api/sittings.ts:39-53`
- **Evidence:** citation — `throwOnClientError` (private, unexported) is declared at `tui/src/api/sittings.ts:39` ahead of the public `openSitting`/`revealBack`/`gradeCard` functions that call it (`tui/src/api/sittings.ts:55,83,103`). Sibling convention (`context/foundation/rules/code-ordering.md` — public before private) holds in at least two siblings: `tui/src/api/cards.ts:19` `export async function listCards(...)` precedes its private helper `tui/src/api/cards.ts:37` `function mapAnchorLocation(...)`; `tui/src/api/stream.ts:102` `export async function* sendMessage(...)` (last public export) precedes the private `tui/src/api/stream.ts:186` `function parseStreamEvent(...)`.
- **Fix:** Move `throwOnClientError` below `gradeCard`, after the public exports, per `context/foundation/rules/code-ordering.md`'s public-before-private rule and both cited siblings.

### R2-F6 — Private render helpers declared before the public default export

- **Severity:** WARNING
- **Dimension:** Pattern Consistency
- **Location:** `tui/src/screens/SittingOverlay.tsx:10-53`
- **Evidence:** citation — `renderOpening`/`renderNothingDue`/`renderPresented`/`renderComplete`/`renderError` (all private, unexported) are declared at `tui/src/screens/SittingOverlay.tsx:10-53`, ahead of `export default function SittingOverlay()` at line 55. Sibling convention holds in at least two siblings: `tui/src/screens/NoteListOverlay.tsx:10` `export default function NoteListOverlay()` precedes its private helpers `clamp`/`NoteRow`/`StatusBadge`/`formatElapsed`; `tui/src/screens/CaptureScreen.tsx:18` `export default function CaptureScreen()` precedes its private helpers (`UserLabel`, `WelesAgentLabel`, `WelesBrand`, and others at lines 126-303).
- **Fix:** Move the five private render helpers below `SittingOverlay`'s default export, per `context/foundation/rules/code-ordering.md`'s public-before-private rule and both cited siblings.

### R2-F7 — `toggleBack` has no re-entrancy guard on the first reveal

- **Severity:** OBSERVATION
- **Dimension:** Safety & Quality
- **Location:** `tui/src/store/sitting.ts:116-147`
- **Evidence:** proof-test — `tui/test/implReviewR2F7_toggleBackRace.test.ts` fails at reviewed HEAD (`ab287f4`): calling `toggleBack` twice before the first call's `revealBack()` promise resolves issues `revealBack` twice (expected once, got two), because the `state.back !== null` guard (`tui/src/store/sitting.ts:131`) only protects a *settled* card, not two rapid presses inside the first reveal's in-flight window.
- **Fix:** `toggleBack` needs an in-flight guard (e.g. checking `lastAction`/a pending flag) for the first-reveal window, not only the `back !== null` check, so the plan's Critical Implementation Details promise — "fetches the back at most once per presented card" — holds under rapid double-press too.

## Retractions

(none)
