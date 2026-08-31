# Coverage Wrap-Up Signal — Plan Brief

> Full plan: `plan.md`

## What & Why

Roadmap slice S-02 wants users to see when the agent thinks a topic is well covered, while staying fully in control of when the conversation actually ends. This plan adds a `coverage_confidence` field on `ConfidenceAssessment` (populated by adapters, threaded to `ReplyDoneEvent`), surfaces it in the TUI as a persistent banner, and locks (unit + BDD) the guarantee that the score never itself closes the conversation.

## Starting Point

`GenerateReplyCommand` already computes a fresh `ConfidenceAssessment` every turn and streams a `ReplyDoneEvent`; `CaptureSession.status` only ever closes via note approval (out of scope here). Nothing today derives an aggregate "covered" judgment from the assessment, and the TUI has no way to show one.

## Desired End State

Every turn's `ConfidenceAssessment` carries `coverage_confidence` (adapters set it; today's deterministic adapter always `0.0`, test double can force `1.0`). `ReplyDoneEvent`/store thread the same value. The TUI shows a persistent green banner between the transcript and the input row whenever the latest score is `>= 1`, and the user can keep chatting normally while it's showing.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| AC-05 signal shape | `coverage_confidence: float` on `ConfidenceAssessment` + `ReplyDoneEvent`, not text copy | Matches LLM structured-output shape; keeps the signal out of reply copy | Plan |
| Coverage rule (today) | Adapters set the field; deterministic adapter always `0.0`, test double `1.0` | No derived-method layer; future LLM adapter maps structured output straight to the field | Plan |
| "User confirms done" (2nd half of AC-06) | No backend action in this slice | Nothing exists yet to trigger (drafting is S-04); matches the ADR's explicit no-`abandon()`/no-`discard()` precedent | Research |
| Unit-test seam | Injectable `ConfidenceAssessmentPort` via `_make_command_stack`, subclass double | Matches the existing `_SpyUnitOfWork` pattern already in this test file | Plan |
| BDD-test seam | Widen `InMemoryCaptureComposition.confidence_assessment` to the port protocol, swap at composition level | The command-level double can't reach the HTTP/SSE stack; this is the actual seam at that layer | Plan |
| TUI surfacing | Persistent green banner, not a toast | Ink has no overlay primitive, and a transient toast doesn't fit a score recomputed every turn | Plan |
| Real coverage algorithm | Out of scope | PRD Open Question 1 explicitly defers "how coverage is computed" past this slice | Research |

## Scope

**In scope:** `coverage_confidence` field on `ConfidenceAssessment` and `ReplyDoneEvent`; adapter population + command threading; unit + BDD regression locking AC-06's negative guarantee; TUI banner (data layer + rendering).

**Out of scope:** any real/smarter coverage-computation algorithm; any backend "confirm conversation done" action; changes to `DeterministicReplyGenerationAdapter`'s reply text; roadmap/stories edits.

## Architecture / Approach

Backend first (score computation → unit lock → BDD lock over HTTP), then TUI (data layer → visible banner) — the same phase ordering S-01 already used for this effort. Every TDD'able unit gets a stubs-then-behavior pair; the BDD and TUI-screen-behavior phases stay single-phase, matching S-01's precedent of writing an acceptance suite green in one phase rather than red-then-green.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Coverage confidence — stubs | `coverage_confidence` field on `ConfidenceAssessment` + DTO field | — |
| 2. Coverage confidence — behavior | Adapter population, threaded into `done`, unit-tested incl. AC-06 guarantee | Test double must genuinely implement `ConfidenceAssessmentPort` to stay swappable |
| 3. BDD (AC-05 & AC-06) | End-to-end HTTP/SSE lock of the same guarantee | Composition-level swap point must not leak into production wiring |
| 4. TUI data layer — stubs | `coverageConfidence` on the event type + store | — |
| 5. TUI data layer — behavior | Parsing + store update, Vitest-covered | — |
| 6. TUI screen — stubs | Banner shell wired into the render tree | — |
| 7. TUI screen — behavior | Real banner, `ink-testing-library`-covered, manual smoke run | The positive case can't be observed live — the shipped deterministic adapter never reaches full coverage |

**Prerequisites:** S-01 (done).
**Estimated effort:** Small — no new aggregates, ports, or endpoints; additive fields and one new UI component threaded through existing seams.

## Open Risks & Assumptions

- The manual verification in Phase 7 can only confirm the banner's *absence* and no regressions — its positive case stays untested outside `ink-testing-library` until a real/smarter confidence adapter ships.
- This plan does not update `context/efforts/capture-flow/roadmap.md`; AC-05 is only partially realized (structural plumbing + test-double coverage, no live-triggerable path) — worth a note next time the roadmap is revisited.

## Success Criteria (Summary)

- `coverage_confidence` is threaded from adapter → assessment → `ReplyDoneEvent`, proven by unit test (`1.0` via test double, `0.0` via deterministic adapter).
- The conversation never closes and further messages keep succeeding regardless of the score, proven by unit test and BDD.
- The TUI shows the green banner exactly when the latest turn's score is `>= 1`, and hides it otherwise, proven by `ink-testing-library`.
