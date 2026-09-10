---
change_id: remember-flow-review-session-tui
current_phase: 8
next_step: 8.1
next_command: /unit-test remember-flow-review-session-tui phase 8
updated: 2026-09-10
---

### Phase 1: API client stubs

#### Automated

- [x] 1.1 Write `api/sittings.ts` type and function signatures — b13f806

#### Manual

- [ ] 1.2 Regenerate `schema.d.ts` against a running backend and confirm the three review-sitting paths are present

### Phase 2: API client behaviour

#### Tests

- [x] tests generated — ada396b

#### Automated

- [x] 2.1 Fill `openSitting`/`revealBack`/`gradeCard` bodies and the `SittingHttpError` throw path — 8dc751c

### Phase 3: Sitting store stubs

#### Automated

- [x] 3.1 Write `store/sitting.ts` state and action signatures — 00ed6c3

### Phase 4: Sitting store behaviour

#### Tests

- [x] tests generated — 37424de

#### Automated

- [x] 4.1 Fill `open`/`toggleBack`/`moveSelection`/`submitGrade`/`retry`/`reset` — beceb42

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

### Phase 8: Wire `/remember` into the app shell

#### Tests

- [ ] tests generated

#### Automated

- [ ] 8.1 Add `isSittingOverlayOpen`/`openSittingOverlay`/`closeSittingOverlay` to `store/index.ts`
- [ ] 8.2 Add the `/remember` command and focus gate in `CaptureScreen.tsx`
- [ ] 8.3 Mount `SittingOverlay` and wire ESC-close + reset in `app.tsx`

#### Manual

- [ ] 8.4 Run the TUI against the live backend and work through a full sitting end to end
