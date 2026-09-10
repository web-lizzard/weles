---
change_id: remember-flow-review-session-tui
current_phase: 1
next_step: 1.1
next_command: /implement remember-flow-review-session-tui phase 1
updated: 2026-09-10
---

### Phase 1: API client stubs

#### Automated

- [ ] 1.1 Write `api/sittings.ts` type and function signatures

#### Manual

- [ ] 1.2 Regenerate `schema.d.ts` against a running backend and confirm the three review-sitting paths are present

### Phase 2: API client behaviour

#### Tests

- [ ] tests generated

#### Automated

- [ ] 2.1 Fill `openSitting`/`revealBack`/`gradeCard` bodies and the `SittingHttpError` throw path

### Phase 3: Sitting store stubs

#### Automated

- [ ] 3.1 Write `store/sitting.ts` state and action signatures

### Phase 4: Sitting store behaviour

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 Fill `open`/`toggleBack`/`moveSelection`/`submitGrade`/`retry`/`reset`

### Phase 5: Sitting overlay stubs

#### Automated

- [ ] 5.1 Write `screens/SittingOverlay.tsx` component signature and per-phase render helper stubs

### Phase 6: Sitting overlay — happy path behaviour

#### Tests

- [ ] tests generated

#### Automated

- [ ] 6.1 Fill loading/front/back-toggle rendering and mount-time `open()` call
- [ ] 6.2 Wire number-key grading, arrow-selection + Enter grading, and card advance

### Phase 7: Sitting overlay — terminal and error states

#### Tests

- [ ] tests generated

#### Automated

- [ ] 7.1 Fill nothing-due and complete state rendering
- [ ] 7.2 Fill error-state rendering and the retry keypress

### Phase 8: Wire `/remember` into the app shell

#### Tests

- [ ] tests generated

#### Automated

- [ ] 8.1 Add `isSittingOverlayOpen`/`openSittingOverlay`/`closeSittingOverlay` to `store/index.ts`
- [ ] 8.2 Add the `/remember` command and focus gate in `CaptureScreen.tsx`
- [ ] 8.3 Mount `SittingOverlay` and wire ESC-close + reset in `app.tsx`

#### Manual

- [ ] 8.4 Run the TUI against the live backend and work through a full sitting end to end
