---
change_id: capture-flow-coverage-wrapup
current_phase: 7
next_step: done
next_command: /archive capture-flow-coverage-wrapup
updated: 2026-08-31
---

### Phase 1: Coverage confidence — stubs

#### Automated

- [x] 1.1 Add `coverage_confidence: float` field to `ConfidenceAssessment`, bounded `Field(ge=0.0, le=1.0)` with a `description` — `application/capture/value_objects.py` — 2d881f4
- [x] 1.2 Add `coverage_confidence: float` field to `ReplyDoneEvent`, bounded `Field(ge=0.0, le=1.0)` — `application/capture/dto.py` — 2d881f4

### Phase 2: Coverage confidence — behavior

#### Tests

- [x] tests generated — c02544f

#### Automated

- [x] 2.1 Set `coverage_confidence` on every `ConfidenceAssessment` returned by `DeterministicConfidenceAssessmentAdapter` (`0.0`)
- [x] 2.2 Thread `coverage_confidence=assessment.coverage_confidence` into `GenerateReplyCommand.handle()`'s `done_event` construction
- [x] 2.3 Extend `_make_command_stack` with an injectable `confidence_assessment` param; add `_AllSolidConfidenceAssessmentAdapter` test double (`coverage_confidence=1.0`)
- [x] 2.4 Write unit tests: `ConfidenceAssessment.coverage_confidence` field bounds, `done_event.coverage_confidence` threading, AC-06 guarantee (session stays `OPEN`, a following `send_message` still succeeds)
- [x] 2.5 `uv run pytest tests/unit/capture -v` green

### Phase 3: Acceptance scenarios (BDD, AC-05 & AC-06)

#### Automated

- [x] 3.1 Widen `InMemoryCaptureComposition.confidence_assessment`'s type to `ConfidenceAssessmentPort` — 49b5e12
- [x] 3.2 Expose the composition to BDD steps via `tests/bdd/conftest.py` — 49b5e12
- [x] 3.3 Write `tests/features/capture-flow/US-02-coverage-wrapup.feature` (AC-05, AC-06 scenarios) — 49b5e12
- [x] 3.4 Write `tests/bdd/steps/coverage_wrapup.py`; register `bdd.steps.coverage_wrapup` in `tests/bdd/test_features.py`'s `pytest_plugins` — 49b5e12
- [x] 3.5 `uv run pytest tests/bdd -m "capture-flow and (AC-05 or AC-06)" -v` green — 49b5e12

### Phase 4: TUI data layer — stubs

#### Automated

- [x] 4.1 Add `coverageConfidence: number` to `ReplyDoneEvent` and `RawReplyStreamEvent`'s done variant — `tui/src/api/stream.ts` — d088012
- [x] 4.2 Add `coverageConfidence: number | null` to `ChatState` — `tui/src/store/chat.ts` — d088012

### Phase 5: TUI data layer — behavior

#### Tests

- [x] tests generated — a78f8b0

#### Automated

- [x] 5.1 Implement `parseStreamEvent`'s `done`-branch `coverageConfidence` parsing — `tui/src/api/stream.ts` — acb6402
- [x] 5.2 Update the chat store's `done`-branch `set(...)` to include `coverageConfidence` — `tui/src/store/chat.ts` — acb6402
- [x] 5.3 Write Vitest tests: SSE parser and store reducer cover `coverageConfidence` — a78f8b0
- [x] 5.4 `pnpm --dir tui test` green — acb6402

### Phase 6: TUI screen — stubs

#### Automated

- [x] 6.1 Add `CoverageBanner` placeholder component (returns `null`), wired in between the transcript `Box` and the `streamError`/input rows — `tui/src/screens/CaptureScreen.tsx` — 273ec95

### Phase 7: TUI screen — behavior

#### Tests

- [x] tests generated — e85ffe3

#### Automated

- [x] 7.1 Implement the real `CoverageBanner` (green banner text, shown when `coverageConfidence >= 1`) — 4db6682
- [x] 7.2 Extend `shouldShowWelesBrand`'s row-budget calculation with a `bannerBlock` term — 4db6682
- [x] 7.3 Write `ink-testing-library` tests: banner shown/hidden per `coverageConfidence` — e85ffe3
- [x] 7.4 `pnpm --dir tui test` green — 4db6682

#### Manual

- [x] 7.5 Run the TUI CLI against the running backend, hold a multi-turn conversation, confirm the banner stays absent and nothing else regresses — 4db6682
