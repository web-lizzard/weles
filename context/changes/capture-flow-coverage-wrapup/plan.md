# Coverage Wrap-Up Signal Implementation Plan

## Overview

Implements roadmap slice S-02 (`Users control when the conversation ends, even when the agent thinks it's done`): a derived `coverage_confidence` score threaded from `ConfidenceAssessment` through the reply stream to the TUI, surfaced as a persistent banner, plus regression coverage (unit + BDD) locking the guarantee that this signal never itself ends the conversation.

## Current State Analysis

- `CaptureSession.status` is binary (`open`/`closed`); the only transition to `closed` is `approve()` → `close()` at note approval (`context/adrs/capture-flow-domain-shape/decision.md:21,25-26,44`) — nothing in the current codebase ever closes a session from confidence/coverage data, so AC-06's negative guarantee already holds by construction and needs only a regression test, not new guard logic.
- `GenerateReplyCommand.handle()` (`backend/src/application/capture/commands/send_message.py:65-85`) already computes a fresh `ConfidenceAssessment` from the full transcript every turn and threads it into `ReplyDoneEvent` — the seam for a coverage score already exists, no new plumbing layer is needed.
- `ConfidenceAssessmentPort.assess(transcript: Transcript)` (`backend/src/application/capture/ports.py:12-13`) already receives the whole transcript, not just the latest message — ruling out "needs broader input" as a reason for a separate port.
- `ConfidenceAssessment` (`backend/src/application/capture/value_objects.py`) is `points: list[ConfidencePoint]`, each `kind: solid|shaky` — a flat list with no aggregate judgment today.
- `DeterministicConfidenceAssessmentAdapter` (`backend/src/adapters/out/in_memory/capture/confidence_assessment.py`) always returns exactly one `SOLID` and one `SHAKY` point for the latest user turn — it can never naturally reach "fully covered" today. Reaching that state for tests requires swapping the port, not tuning this adapter.
- `InMemoryCaptureComposition` (`backend/tests/integration/support/in_memory_capture.py`) pins `confidence_assessment` to the concrete `DeterministicConfidenceAssessmentAdapter` type, so BDD/HTTP-level tests cannot swap in a different assessment today.
- The TUI (`tui/src/screens/CaptureScreen.tsx`) is Ink + `ink-text-input` + zustand (`tui/src/store/chat.ts`); no toast/overlay primitive exists in Ink or in this codebase — the closest existing precedent is `StatusBar`, a conditionally-rendered `Box` sitting between the transcript and the input row.
- `tui/src/api/stream.ts`'s `done` event already threads one derived scalar (`topic`) from the backend DTO into the store on every turn (`tui/src/store/chat.ts:61-69`) — the pattern this change's TUI phases repeat for `coverage_confidence`.

### Key Discoveries:
- `context/adrs/capture-flow-domain-shape/decision.md:44` and `:67,80` — the ADR's explicit YAGNI stance (no `abandon()`/`discard()`, rejected for protecting against nothing functional) is the basis for building no backend "confirm done" action in this slice.
- `backend/tests/unit/capture/test_send_message_command.py:211-226` — `_SpyUnitOfWork(InMemoryUnitOfWork)` is this codebase's established pattern for a test-only port implementation swapped in via constructor injection; the new `_AllSolidConfidenceAssessmentAdapter` follows the same shape.
- `context/archive/changes/2026-08-29-capture-flow-socratic-conversation/todos.md` (Phase 9) — the precedent for a BDD phase: single phase, no `#### Tests` row, feature file + step module + `pytest_plugins` registration, verified green in the same phase it's written.
- `context/archive/changes/2026-08-29-capture-flow-socratic-conversation/todos.md` (Phases 10-13) — the precedent for TUI phases: stub phase adds a static placeholder wired into the render tree, behavior phase implements real logic/styling and adds `ink-testing-library`/Vitest tests.

## Desired End State

- `ReplyDoneEvent` (backend) and its TUI counterpart carry a `coverage_confidence`/`coverageConfidence` score derived purely from the turn's `ConfidenceAssessment`.
- A unit test proves the score is `1.0` exactly when the assessment has no shaky points, `0.0` otherwise, and that neither value ever affects `CaptureSession.status` or blocks a following `send_message` call.
- A BDD scenario proves the same guarantee end-to-end over HTTP/SSE.
- The TUI shows a persistent green banner between the transcript and the input row whenever the latest turn's `coverageConfidence >= 1`, and shows nothing otherwise; sending another message still works while the banner is showing.

Verification: `cd backend && uv run pytest tests/unit/capture -v`, `cd backend && uv run pytest tests/bdd -m "capture-flow and (AC-05 or AC-06)" -v`, `pnpm --dir tui test`, plus the manual TUI run in Phase 7.

## What We're NOT Doing

- **Real coverage computation.** `DeterministicConfidenceAssessmentAdapter` is untouched and still always returns one solid + one shaky point — it can never trigger `coverage_confidence == 1.0` in a real run today. This change builds the plumbing and proves it via test doubles; a smarter/real assessment adapter is future work (PRD Open Question 1, explicitly deferred).
- **Any backend action for "the user explicitly confirms they're done."** Nothing in this slice hooks into that half of AC-06 — there is nothing yet for a confirmation to trigger (drafting is S-04, out of scope here), and the ADR's precedent (no `abandon()`/`discard()`) argues against adding a consumer-less endpoint now.
- **Changing `DeterministicReplyGenerationAdapter`'s reply copy.** The wrap-up signal is a structured field, not a text branch — the deterministic adapter's "Let's dig into: ..." phrasing is left exactly as-is; a future LLM-backed adapter owns expressing coverage in natural language.
- **A toast/overlay component.** Ink has no overlay primitive; the signal is a persistent conditionally-rendered banner, not a transient notification.
- **Updating `context/efforts/capture-flow/roadmap.md` or `stories.md`.** This plan only partially realizes AC-05 as originally scoped (see Critical Implementation Details) — flagging the roadmap's AC mapping is left to whoever next runs `/roadmap`, not this plan.

## Implementation Approach

Backend first (score computation, then its regression lock at both the command level and the HTTP/BDD level), then TUI (data layer, then the visible banner) — mirroring the exact phase ordering S-01 already established for this effort. Each TDD'able unit gets a stubs-then-behavior pair; the two BDD phases (backend, already covered above) and the feature-file/step work stay single-phase, matching the precedent in S-01's Phase 9 where the acceptance suite was written and turned green in one phase rather than red-then-green.

## Critical Implementation Details

`coverage_confidence` is deliberately a float bounded to `[0.0, 1.0]` (enforced via `Field(ge=0.0, le=1.0)` on `ReplyDoneEvent`), even though today's computation is binary (`1.0` or `0.0`) — the bound and type leave room for a future assessment adapter to return a graded score without a contract change. Treat `>= 1` as the trigger threshold everywhere (TUI banner, BDD assertions), not `== 1.0`, so a future fractional adapter can adjust the underlying computation without every consumer needing a matching change.

## Phase 1: Coverage confidence — stubs

### Overview
Materialize the new symbols both later phases build on: the derived-score method and the DTO field that carries it.

### Changes Required:

#### 1. Coverage confidence method signature

**File**: `backend/src/application/capture/value_objects.py`

**Intent**: Give `ConfidenceAssessment` a single, reusable place to express "how covered is this," independent of any specific adapter.

**Contract**: Add to `ConfidenceAssessment`:
```python
def coverage_confidence(self) -> float:
    raise NotImplementedError
```

#### 2. DTO field

**File**: `backend/src/application/capture/dto.py`

**Intent**: Carry the score across the wire so BDD and the TUI can read it without recomputing it from raw points.

**Contract**: Add to `ReplyDoneEvent`:
```python
coverage_confidence: float = Field(
    ge=0.0,
    le=1.0,
    description=(
        "How fully the agent judges the topic covered as of this turn, "
        "0.0-1.0; 1.0 means no shaky points remain."
    ),
)
```

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run python -c "import application.capture.value_objects, application.capture.dto"` (module imports cleanly)

---

## Phase 2: Coverage confidence — behavior

### Overview
Implement the computation, thread it into the command's `done` event, and lock both the score's correctness and the AC-06 negative guarantee.

### Changes Required:

#### 1. Implement `coverage_confidence`

**File**: `backend/src/application/capture/value_objects.py`

**Intent**: Realize the coverage rule settled in planning: fully covered exactly when nothing shaky remains.

**Contract**: `coverage_confidence()` returns `1.0` when `self.points` is non-empty and every point's `kind == ConfidencePointKind.SOLID`; `0.0` otherwise (including the empty-points case). Always within `[0.0, 1.0]`, matching the `ReplyDoneEvent.coverage_confidence` field's `Field(ge=0.0, le=1.0)` bound from Phase 1.

#### 2. Thread the score into the reply

**File**: `backend/src/application/capture/commands/send_message.py`

**Intent**: Make the score observable on every turn without a second read of the transcript.

**Contract**: `GenerateReplyCommand.handle()` passes `coverage_confidence=assessment.coverage_confidence()` when constructing `done_event`.

#### 3. Injectable confidence-assessment test seam

**File**: `backend/tests/unit/capture/test_send_message_command.py`

**Intent**: Let a test force a fully-covered assessment without touching production adapters.

**Contract**: `_make_command_stack` gains an optional `confidence_assessment: ConfidenceAssessmentPort | None = None` parameter, defaulting to `DeterministicConfidenceAssessmentAdapter()`; add `_AllSolidConfidenceAssessmentAdapter` (a small class implementing `ConfidenceAssessmentPort`, returning only `SOLID` points), following the `_SpyUnitOfWork` precedent already in this file.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/test_application_value_objects.py -v` — `coverage_confidence` is `1.0` for all-solid points, `0.0` for empty points and for mixed solid/shaky points.
- `cd backend && uv run pytest tests/unit/capture/test_send_message_command.py -v` — `done_event.coverage_confidence == 1.0` when `_AllSolidConfidenceAssessmentAdapter` is injected; `== 0.0` with the default deterministic adapter; the session's `status` stays `OPEN` after an all-solid turn; a following `send_message` call on the same session still succeeds (no `CaptureSessionClosedError`).

---

## Phase 3: Acceptance scenarios (BDD, AC-05 & AC-06)

### Overview
Lock the same score-and-guarantee behavior end-to-end over HTTP/SSE, matching the precedent set by S-01's Phase 9.

### Changes Required:

#### 1. Swappable confidence assessment in the HTTP-level composition

**File**: `backend/tests/integration/support/in_memory_capture.py`

**Intent**: Let a BDD scenario force a fully-covered assessment through the real FastAPI route, not just the in-process command.

**Contract**: Widen `InMemoryCaptureComposition.confidence_assessment`'s type annotation from `DeterministicConfidenceAssessmentAdapter` to `ConfidenceAssessmentPort`; `create()`'s default is unchanged.

#### 2. Expose the composition to BDD steps

**File**: `backend/tests/bdd/conftest.py`

**Intent**: Give step functions a handle to swap `confidence_assessment` before a scenario's request.

**Contract**: The fixture that builds `InMemoryCaptureComposition` also exposes it (directly or via a sibling fixture) to steps, alongside the existing `capture_client` fixture.

#### 3. Feature file

**File**: `backend/tests/features/capture-flow/US-02-coverage-wrapup.feature` (new)

**Intent**: Acceptance scenarios for AC-05 and AC-06.

**Contract**: Two scenarios tagged `@capture-flow @AC-05` and `@capture-flow @AC-06` respectively, in the Given/When/Then style of `US-01-socratic-conversation.feature` — AC-05's scenario asserts the `done` event's coverage score reads as fully covered after an all-solid turn; AC-06's scenario sends a further message after that turn and asserts it still succeeds.

#### 4. Step definitions

**File**: `backend/tests/bdd/steps/coverage_wrapup.py` (new)

**Intent**: Back the new feature file.

**Contract**: A `Given` step swaps the composition's `confidence_assessment` for an all-solid double; `Then` steps assert the coverage score and that a follow-up `send_message` call still returns a normal `done` event.

#### 5. Register the step module

**File**: `backend/tests/bdd/test_features.py`

**Intent**: Make the new steps discoverable by `pytest-bdd`.

**Contract**: Add `"bdd.steps.coverage_wrapup"` to `pytest_plugins`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/bdd -m "capture-flow and (AC-05 or AC-06)" -v`

---

## Phase 4: TUI data layer — stubs

### Overview
Materialize the new field on the TUI's event type and store shape.

### Changes Required:

#### 1. Event type field

**File**: `tui/src/api/stream.ts`

**Intent**: Give the store something to read the score off of.

**Contract**: Add `coverageConfidence: number` to the `ReplyDoneEvent` type and to `RawReplyStreamEvent`'s `done` variant (`coverage_confidence: number`).

#### 2. Store field

**File**: `tui/src/store/chat.ts`

**Intent**: Hold the latest turn's score for the screen to read.

**Contract**: Add `coverageConfidence: number | null` to `ChatState`, initialized to `null`.

### Success Criteria:

#### Automated Verification:
- `pnpm --dir tui exec tsc --noEmit` (types compile)

---

## Phase 5: TUI data layer — behavior

### Overview
Parse the field off the wire and update the store on every turn, mirroring how `topic` already flows.

### Changes Required:

#### 1. Parse the field

**File**: `tui/src/api/stream.ts`

**Intent**: Surface the backend's score to the rest of the TUI.

**Contract**: `parseStreamEvent`'s `done` branch returns `coverageConfidence: raw.coverage_confidence`.

#### 2. Update store on `done`

**File**: `tui/src/store/chat.ts`

**Intent**: Keep the score current with the latest turn, same lifecycle as `topic`.

**Contract**: The `done`-branch `set(...)` call (`tui/src/store/chat.ts:62-69`) adds `coverageConfidence: event.coverageConfidence` alongside `topic: event.topic`.

### Success Criteria:

#### Automated Verification:
- `pnpm --dir tui test` — extended SSE-parser test asserts `coverageConfidence` is parsed from `coverage_confidence`; extended store-reducer test asserts `coverageConfidence` updates on a `done` event.

---

## Phase 6: TUI screen — stubs

### Overview
Wire a placeholder banner into the render tree at the confirmed position — between the transcript and the input row.

### Changes Required:

#### 1. Banner component shell

**File**: `tui/src/screens/CaptureScreen.tsx`

**Intent**: Reserve the render-tree slot without changing visible behavior yet, matching the `CaptureScreen.tsx` stub precedent from S-01 Phase 12.

**Contract**:
```tsx
function CoverageBanner({
  coverageConfidence,
}: {
  coverageConfidence: number | null;
}) {
  return null;
}
```
Called as `<CoverageBanner coverageConfidence={coverageConfidence} />` immediately after the transcript `Box` (`tui/src/screens/CaptureScreen.tsx:62`) and before the `streamError` check — i.e., between the transcript and the input row.

### Success Criteria:

#### Automated Verification:
- `pnpm --dir tui exec tsc --noEmit`

---

## Phase 7: TUI screen — behavior

### Overview
Make the banner real: a persistent green line shown while the latest turn reads as fully covered, with no effect on the ability to keep chatting.

### Changes Required:

#### 1. Render the real banner

**File**: `tui/src/screens/CaptureScreen.tsx`

**Intent**: Give the user a visible cue for AC-05 without ending or blocking the conversation (AC-06).

**Contract**: `CoverageBanner` renders `<Box marginY={1}><Text color="green">✓ This topic seems well covered — keep going, or wrap up when you're ready.</Text></Box>` when `coverageConfidence !== null && coverageConfidence >= 1`, else `null`. `shouldShowWelesBrand`'s row-budget calculation (`tui/src/screens/CaptureScreen.tsx:113-145`) gains a `bannerBlock` term, sized like `errorBlock`, so the banner doesn't starve the transcript when both are visible.

### Success Criteria:

#### Automated Verification:
- `pnpm --dir tui test` — `ink-testing-library` test: banner text appears when the store's `coverageConfidence` is `>= 1`; absent when `null` or `< 1`; positioned after the transcript content.

#### Manual Verification:
- Run the TUI CLI against the running backend and hold a normal multi-turn conversation: confirm the banner stays absent throughout (the shipped `DeterministicConfidenceAssessmentAdapter` never reaches full coverage) and that nothing else regresses — chat, streaming, and the topic heading all behave as before. Observing the banner's positive case live is not possible until a smarter confidence adapter exists (see What We're NOT Doing).

---

## Testing Strategy

### Unit Tests:
- `backend/tests/unit/capture/test_application_value_objects.py` — `coverage_confidence()` pure-function cases.
- `backend/tests/unit/capture/test_send_message_command.py` — `done_event.coverage_confidence` threading, plus the AC-06 negative guarantee (session stays open, next message succeeds).
- `tui` Vitest suites for the SSE parser and the chat store reducer.
- `tui` `ink-testing-library` suite for `CoverageBanner`'s conditional rendering.

### Integration Tests:
- `backend/tests/bdd/features/capture-flow/US-02-coverage-wrapup.feature` via `pytest-bdd`, over the real HTTP/SSE stack.

### Manual Testing Steps:
- Phase 7's manual verification (TUI smoke run, banner-absence + no-regression check).

## Performance Considerations

None — `coverage_confidence` is an O(n) scan over an already-loaded, per-turn points list; no new I/O or query is introduced.

## Migration Notes

None — additive field on `ReplyDoneEvent`/`ReplyDoneEvent`'s TUI counterpart; no existing consumer breaks on an unknown-but-ignored field, and no persisted schema changes.

## References

- `context/changes/capture-flow-coverage-wrapup/research.md` — ADR-derived domain-model constraints for this slice.
- `context/adrs/capture-flow-domain-shape/decision.md` — governing domain model (CaptureSession/Message shape, YAGNI precedent).
- `context/efforts/capture-flow/prd.md` — FR-004, FR-005, Open Question 1 (coverage computation deferred).
- `context/efforts/capture-flow/stories.md` — US-02, AC-05, AC-06.
- `context/efforts/capture-flow/roadmap.md` — S-02 slice definition.
- `context/archive/changes/2026-08-29-capture-flow-socratic-conversation/` — S-01's plan/todos, source of every phase-shape and stub-convention precedent cited above.

See `todos.md` for execution state.
