# Distill Generates Cards End to End Against a Real Provider — Plan Brief

> Full plan: `plan.md`

## What & Why
Distill's single model call becomes a domain-held flow — generate, review, regenerate the
gaps at most once, review replacements, merge duplicates — so weak and duplicate cards are
filtered before persistence, with routing and pass/fail policy testable without a model
(FR-04, FR-05), running against a real provider traced in Langfuse (FR-08) through adapters
the domain does not know (FR-09).

## Starting Point
The whole contract (run, phases, graph, builders, policy, port) is on disk with unimplemented
bodies; the command still uses the old single-shot `CardGeneration` seam.

## Desired End State
A saved note walks the graph to `MERGING`; every minted card, surviving or discarded, is
persisted and the note ends `READY` (even with zero cards). Any model failure leaves the note
`FAILED` with nothing saved. Live, each run is one Langfuse session with a span per model call.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Flow vehicle | Acyclic `StructuredStateMachine`, command loops over `advance` | Keeps routing in the domain without a dispatcher class | Frame / Contracts |
| Model seam | One phase-agnostic `StructuredTaskPort.complete(instruction, output)` | Phase declares both, so adapters have nothing to dispatch on | Contracts |
| Verdict coverage | Unknown refs ignored; unjudged → `LOW_QUALITY` "no verdict" | Nothing unreviewed reaches the user | Plan |
| Same-round merge tie | Earlier-proposed candidate survives | Deterministic, model-free rule | Plan |
| Unmintable proposal | Counts in share, not persisted, a gap | Garbage rounds cannot dodge regeneration | Plan |
| Grade scale | POOR < WEAK < SOUND < STRONG, pass from SOUND | Even scale forces a stance | Plan |
| Phase failure | Note `FAILED`, nothing persisted; no adapter retry policy | Matches today; shared adapter error handling is its own change | Plan |
| Deterministic regeneration | `GAPS` block present → empty proposals | Thin adapter, BDD unchanged, no duplicated cards | Plan |
| Threshold tiers | ≤1500: 0.5 · ≤6000: 0.6 · open: 0.7 | Starting heuristic, tuned empirically | Plan |

## Scope

**In scope:** `advance`; all distill run/policy/grade/builder/machine behaviour; deterministic and pydantic-ai `StructuredTaskPort` adapters; command loop; removal of `CardGeneration`; settings, composition, run parent span; manual live verification.
**Out of scope:** shared LLM adapter error handling (separate change), flow recovery, persisting partial runs, Langfuse scores, capture's graph walk, roadmap prose fixes.

## Architecture / Approach
Inside-out: shared mechanic → domain rules → run behaviour (mint, review, merge) → builders →
machine route → deterministic adapter → command + seam swap → real adapter → live wiring.
Test-first throughout, except the two adapters: discover-contracts-log.md flagged both as
never stubbed, so each gets its own stubs-and-interfaces phase first (Revision 1).

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. `advance` | Guard-selected move | Ambiguous-guard refusal semantics |
| 2. Grade & policy | Pass line, tier threshold | Tier boundary off-by-one |
| 3. Run minting | Candidates through gates | Unmintable handling vs factory exceptions |
| 4. Run review | Verdicts, share, gaps | Replacement review touching round 1 |
| 5. Run merge | Survivor rule | Tie ordering |
| 6. Builders | Phase prose, required blocks | `NOTE` block shape the deterministic adapter reads |
| 7. Machine & route | Walkable graph, both routes proven | Empty-phase answers |
| 8. Deterministic adapter — stubs | Class + method shape, no behaviour | — |
| 9. Deterministic adapter | In-memory port + contract | Keeping BDD's control card |
| 10. Command & seam swap | Loop, persistence, old seam gone | Constructor change breaks compose/BDD |
| 11. pydantic-ai adapter — stubs | Class + method shape, no behaviour | — |
| 12. pydantic-ai adapter | Structured calls, per-call spans | pydantic-ai output API details |
| 13. Live wiring | Settings, provider switch, run span, manual FR-08 | Real-model output quality |

**Prerequisites:** S-01, S-03, S-04 archived done; OpenRouter and Langfuse keys for Phase 13.
**Estimated effort:** 13 phases — 11 test-first (2–6 tests each) plus 2 stubs-and-interfaces.

## Open Risks & Assumptions
- Real-model review may grade harshly and trigger regeneration often; tiers are tunable in settings.
- Two review phases share one output type, so their spans share a name and are told apart by order.
- Adapter-level retries and failure classification are deferred to a separate change.

## Success Criteria (Summary)
- Full backend suite, basedpyright and ruff clean; BDD distill-flow unchanged and green.
- Distill graph proven model-free: terminal `{MERGING}`, acyclic, both routes walked.
- Manual live run: cards persisted, note `READY`, one Langfuse session per note with per-phase spans.
