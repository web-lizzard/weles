---
change_id: remember-flow-review-session-tui
current_phase: 8
next_step: 8.4
next_command: /implement remember-flow-review-session-tui phase 8
updated: 2026-09-10
---

### Phase 1: API client stubs

#### Automated

- [x] 1.1 Write `api/sittings.ts` type and function signatures — b13f806

#### Manual

- [x] 1.2 Regenerate `schema.d.ts` against a running backend and confirm the three review-sitting paths are present — 0c0fd6c

#### Triage

- [x] 1.3 R1-F1 OpenAPI schema lacks review-sitting paths (proof: e9a4f2e) — d36b28a

### Phase 2: API client behaviour

#### Tests

- [x] tests generated — ada396b

#### Automated

- [x] 2.1 Fill `openSitting`/`revealBack`/`gradeCard` bodies and the `SittingHttpError` throw path — 8dc751c

#### Triage

- [x] 2.2 R1-F2 Sitting API uses raw fetch instead of openapi client — 043b0cd
- [x] 2.3 R2-F1 api/client.ts modified outside any phase's Changes Required — 28847ba
- [x] 2.4 R2-F2 Untested cross-cutting change to the shared fetch delegate — 28847ba
- [x] 2.5 R2-F3 openSitting raises on the backend's own "just completed, no card" response (proof: 48ebc3f) — 28847ba
- [x] 2.6 R2-F5 Private helper declared before the public functions that use it — 28847ba

### Phase 3: Sitting store stubs

#### Automated

- [x] 3.1 Write `store/sitting.ts` state and action signatures — 00ed6c3

### Phase 4: Sitting store behaviour

#### Tests

- [x] tests generated — 37424de

#### Automated

- [x] 4.1 Fill `open`/`toggleBack`/`moveSelection`/`submitGrade`/`retry`/`reset` — beceb42

#### Triage

- [x] 4.2 R2-F4 submitGrade has no re-entrancy guard (proof: 48ebc3f) — 1754a81
- [x] 4.3 R2-F7 toggleBack has no re-entrancy guard on the first reveal (proof: 48ebc3f) — 1754a81

### Phase 5: Sitting overlay stubs

#### Automated

- [x] 5.1 Write `screens/SittingOverlay.tsx` component signature and per-phase render helper stubs — 54c1dfa

### Phase 6: Sitting overlay — happy path behaviour

#### Tests

- [x] tests generated — e16d56e

#### Automated

- [x] 6.1 Fill loading/front/back-toggle rendering and mount-time `open()` call — c454f7f
- [x] 6.2 Wire number-key grading, arrow-selection + Enter grading, and card advance — c454f7f

### Phase 7: Sitting overlay — terminal and error states

#### Tests

- [x] tests generated — ccf47a8

#### Automated

- [x] 7.1 Fill nothing-due and complete state rendering — c2b8fc5
- [x] 7.2 Fill error-state rendering and the retry keypress — c2b8fc5

#### Triage

- [x] 7.3 R2-F6 Private render helpers declared before the public default export — 4ebca7a

### Phase 8: Wire `/remember` into the app shell

#### Tests

- [x] tests generated — e049cfa

#### Automated

- [x] 8.1 Add `isSittingOverlayOpen`/`openSittingOverlay`/`closeSittingOverlay` to `store/index.ts` — 6041d50
- [x] 8.2 Add the `/remember` command and focus gate in `CaptureScreen.tsx` — 6041d50
- [x] 8.3 Mount `SittingOverlay` and wire ESC-close + reset in `app.tsx` — 6041d50

#### Manual

- [ ] 8.4 Run the TUI against the live backend and work through a full sitting end to end
