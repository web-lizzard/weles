---
change_id: capture-flow-coverage-wrapup
current_phase: 2
next_step: 2.1
next_command: /unit-test capture-flow-coverage-wrapup phase 2
updated: 2026-08-31
---

### Phase 1: Coverage confidence — stubs

#### Automated

- [x] 1.1 Add `coverage_confidence: float` field to `ConfidenceAssessment`, bounded `Field(ge=0.0, le=1.0)` with a `description` — `application/capture/value_objects.py` — 2d881f4
- [x] 1.2 Add `coverage_confidence: float` field to `ReplyDoneEvent`, bounded `Field(ge=0.0, le=1.0)` — `application/capture/dto.py` — 2d881f4

### Phase 2: Coverage confidence — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 2.1 Set `coverage_confidence` on every `ConfidenceAssessment` returned by `DeterministicConfidenceAssessmentAdapter` (`0.0`)
- [ ] 2.2 Thread `coverage_confidence=assessment.coverage_confidence` into `GenerateReplyCommand.handle()`'s `done_event` construction
- [ ] 2.3 Extend `_make_command_stack` with an injectable `confidence_assessment` param; add `_AllSolidConfidenceAssessmentAdapter` test double (`coverage_confidence=1.0`)
- [ ] 2.4 Write unit tests: `ConfidenceAssessment.coverage_confidence` field bounds, `done_event.coverage_confidence` threading, AC-06 guarantee (session stays `OPEN`, a following `send_message` still succeeds)
- [ ] 2.5 `uv run pytest tests/unit/capture -v` green

### Phase 3: Acceptance scenarios (BDD, AC-05 & AC-06)

#### Automated

- [ ] 3.1 Widen `InMemoryCaptureComposition.confidence_assessment`'s type to `ConfidenceAssessmentPort`
- [ ] 3.2 Expose the composition to BDD steps via `tests/bdd/conftest.py`
- [ ] 3.3 Write `tests/features/capture-flow/US-02-coverage-wrapup.feature` (AC-05, AC-06 scenarios)
- [ ] 3.4 Write `tests/bdd/steps/coverage_wrapup.py`; register `bdd.steps.coverage_wrapup` in `tests/bdd/test_features.py`'s `pytest_plugins`
- [ ] 3.5 `uv run pytest tests/bdd -m "capture-flow and (AC-05 or AC-06)" -v` green

### Phase 4: TUI data layer — stubs

#### Automated

- [ ] 4.1 Add `coverageConfidence: number` to `ReplyDoneEvent` and `RawReplyStreamEvent`'s done variant — `tui/src/api/stream.ts`
- [ ] 4.2 Add `coverageConfidence: number | null` to `ChatState` — `tui/src/store/chat.ts`

### Phase 5: TUI data layer — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 5.1 Implement `parseStreamEvent`'s `done`-branch `coverageConfidence` parsing — `tui/src/api/stream.ts`
- [ ] 5.2 Update the chat store's `done`-branch `set(...)` to include `coverageConfidence` — `tui/src/store/chat.ts`
- [ ] 5.3 Write Vitest tests: SSE parser and store reducer cover `coverageConfidence`
- [ ] 5.4 `pnpm --dir tui test` green

### Phase 6: TUI screen — stubs

#### Automated

- [ ] 6.1 Add `CoverageBanner` placeholder component (returns `null`), wired in between the transcript `Box` and the `streamError`/input rows — `tui/src/screens/CaptureScreen.tsx`

### Phase 7: TUI screen — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 7.1 Implement the real `CoverageBanner` (green banner text, shown when `coverageConfidence >= 1`)
- [ ] 7.2 Extend `shouldShowWelesBrand`'s row-budget calculation with a `bannerBlock` term
- [ ] 7.3 Write `ink-testing-library` tests: banner shown/hidden per `coverageConfidence`
- [ ] 7.4 `pnpm --dir tui test` green

#### Manual

- [ ] 7.5 Run the TUI CLI against the running backend, hold a multi-turn conversation, confirm the banner stays absent and nothing else regresses
