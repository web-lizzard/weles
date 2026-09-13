# Distill Generates Cards End to End Against a Real Provider — Implementation Plan

Execution state lives in `todos.md` (sibling of this file), per the `/plan` skill's `references/todos-format.md`.

## Overview

Distill's card generation becomes a domain-held, acyclic phase flow — generate, review,
conditionally regenerate and review the replacements, then merge — walked by
`GenerateCardsCommand` through one phase-agnostic `StructuredTaskPort`, with a
deterministic adapter for tests and BDD and a pydantic-ai adapter for the real provider,
every model call traced in Langfuse under one parent span per run. This is slice S-06 of
effort `llm-adapter` and delivers FR-04, FR-05, FR-08 and FR-09 for distill.

## Current State Analysis

- The contract is on disk (commit `f73d48a`, closed `discover-contracts.md`): `DistillRun`,
  `Candidate`, the three output events, `DistillMachine` with five `StructuredState`s and the
  graph, four instruction builders, `RegenerationPolicy`, `ReviewGrade`, `CardVerdict`,
  `DuplicateGroup`, `StructuredTaskPort`, `DistillDeps`. Every behaviour body is `...` or
  `NotImplementedError` — including the shared `StateMachine.advance`.
- `GenerateCardsCommand` (`backend/src/application/distill/commands/generate_cards.py:19-72`)
  still makes one `CardGeneration.generate` call and mints inline; it is wired in
  `backend/src/adapters/compose.py:125,236-240` and
  `backend/tests/integration/support/in_memory_distill.py:35-72`.
- `CardGeneration` (`backend/src/application/distill/ports.py:9-10`) and
  `DeterministicCardGenerationAdapter`
  (`backend/src/adapters/out/in_memory/distill/card_generation.py`) are the old single-shot
  seam, with a contract suite at
  `backend/tests/unit/distill/contracts/test_card_generation_contract.py`.
- BDD `distill-flow` scenarios AC-03..AC-06 (`backend/tests/features/distill-flow/US-02*`,
  `US-03*`) depend on the deterministic generator's shape: block-derived grounded proposals
  plus one fabricated ungrounded control card.
- No distill LLM adapter exists; `adapters/out/llm/` holds capture only. `observation`
  (`backend/src/adapters/out/llm/tracing.py:32-51`) is the Langfuse span helper.
- Roadmap prerequisites S-01, S-03, S-04 are archived `done`; the change.md caveat about S-03
  is stale.

## Desired End State

A saved note triggers one card-generation run that walks the distill graph to `MERGING`
without the command choosing a route. Every minted card — surviving or discarded
(`UNGROUNDED`, `OVERSIZED`, `LOW_QUALITY`, `DUPLICATE`) — is persisted and the note ends
`READY`, including when no card survives. Any model-call exception, or a walk that stops
short of the terminal phase, leaves the note `FAILED` with nothing persisted. With
`DISTILL_TASK_PROVIDER=pydantic_ai`, the run executes against OpenRouter and Langfuse shows
one parent span per note (session = note id) with one child span per model call.

Verify: `cd backend && uv run pytest` green (unit, contracts, integration, BDD),
`uv run basedpyright` and `uv run ruff check src tests` clean, and the manual live run in
Phase 11.

### Key Discoveries:
- `StructuredStateMachine` docstring (`backend/src/domain/shared/graph/machine.py:158-178`)
  is the command loop verbatim — the command implements exactly that and nothing more.
- Guards read only the context (`EdgeCondition`), which is why the policy rides on
  `DistillRun.policy` (`backend/src/domain/distill/run.py:75`).
- `Instruction` enforces required blocks at construction
  (`backend/src/domain/shared/instruction/model.py:102-114`) — FR-05's guard is a type
  invariant, so builder tests assert `required` and presence, not a dispatcher check.
- Capture's builder shape to mirror: general floor unioned into `phase_required`
  (`backend/src/domain/capture/instructions.py:29-60`).
- Adapter test pattern: `models.ALLOW_MODEL_REQUESTS = False`, `TestModel`/`FunctionModel`,
  in-memory span exporter (`backend/tests/unit/capture/test_pydantic_ai_capture_agent.py:1-58`).
- pydantic-ai 2.35.3: `Agent.run(..., output_type=..., instructions=...)`.
- Composition selects providers by settings enum with lazy pydantic-ai imports
  (`backend/src/adapters/compose.py:133-150`).

## What We're NOT Doing

- **Shared error handling for LLM adapters** (retry, backoff, classification of provider
  failures). It is cross-cutting — capture has the same gap — so it belongs in its own
  change (suggested: `/new-container llm-adapter-error-handling`). Here the pydantic-ai
  adapter propagates whatever pydantic-ai raises, with no bespoke retry policy.
- Recovering or resuming an interrupted run (frame: out of scope).
- Persisting a run's phase or any partial result on failure.
- Langfuse scores or evaluation of review verdicts (tracing only).
- Capture's graph walk with `advance` (change `capture-command-graph-walk`).
- Rewriting roadmap S-06's stale prose ("single-shot", "without a transition graph") — `/roadmap`'s.
- A domain cap on replacement count (instruction-steered only).

## Implementation Approach

Inside-out along the dependency order the contract already fixes: shared mechanic
(`advance`) → domain value rules → `DistillRun` behaviour in three slices → instruction
builders → machine wiring and route → deterministic port adapter → command loop and seam
swap (BDD must stay green) → real-provider adapter → live composition and tracing. Every
phase is a behaviour phase with failing tests first; no stubs phase, because the contract
is already in the working tree.

Rules settled in planning (beyond frame and contract sessions):

| Rule | Decision |
| --- | --- |
| verdict-coverage | Unknown refs ignored; a candidate awaiting review with no verdict is discarded `LOW_QUALITY`, detail `no verdict`, and counts as a gap |
| merge-tie-same-round | Equal grade, same round: the earlier-proposed candidate (lower ref sequence) survives |
| unmintable-proposal | Counts toward the round's share, `card=None`, not persisted, a gap with failure `could not become a card` |
| grade-scale | `POOR < WEAK < SOUND < STRONG`, passes from `SOUND` |
| phase failure | Any port exception → note `FAILED`, nothing persisted |
| deterministic regeneration | Instruction carrying a `GAPS` block → empty proposals |
| threshold tiers | ≤1500 chars: 0.5; ≤6000: 0.6; open: 0.7 |

## Critical Implementation Details

Phase 9 is the only phase that changes a constructor other suites build: `compose.py`,
`tests/integration/support/in_memory_distill.py`, and the two command/handler unit suites
must move in the same phase, or BDD and `adapters.compose` import break. The persist step
must run only after the walk ends in a terminal phase — persisting inside the loop would
contradict "nothing persisted on failure".

## Phase 1: Guard-selected move on the shared machine

### Overview
Implement `StateMachine.advance`, the one shared mechanic distill's walk depends on.

### Changes Required:

#### 1. Advance
**File**: `backend/src/domain/shared/graph/machine.py`

**Intent**: Take the single move whose guard passes, through `transition`, so a guard-routed flow never has its caller name a target.

**Contract**: `async def advance(self) -> bool` — `False` when the current state is terminal, when no outgoing guard passes, or when more than one passes; otherwise delegates to `transition(target)` (edge actions run, state written) and returns `True`. An unguarded edge counts as passing. Built on `available_transitions`.

**File**: `backend/tests/unit/shared/test_graph_machine.py`

**Intent**: Pin the four outcomes on the existing test graph fixtures.

**Contract**: flat `test_advance_…` functions; no new shared fixtures.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/shared/test_graph_machine.py -v` passes
- `cd backend && uv run basedpyright src/domain/shared` reports 0 errors

---

## Phase 2: Review grade and regeneration policy rules

### Overview
The two pure rules the run's queries stand on.

### Changes Required:

#### 1. Review grade
**File**: `backend/src/domain/distill/value_objects.py`

**Intent**: Give the ordered scale its order and the domain's pass line.

**Contract**: `ReviewGrade.rank -> int` follows declaration order (POOR lowest); `ReviewGrade.passes -> bool` is true for `SOUND` and `STRONG` only.

#### 2. Regeneration policy
**File**: `backend/src/domain/distill/regeneration.py`

**Intent**: Decide whether a first round regenerates from its accepted share and the note's length tier.

**Contract**: `RegenerationPolicy.regenerate(content, accepted, proposed) -> bool` — tier is the first whose `max_length` is `None` or ≥ `len(content.value)`; returns `proposed == 0 or accepted / proposed < tier.min_accepted_share`. Tier ordering invariant is validated at construction (ascending `max_length`, exactly the last one open), raising `ValueError`.

**File**: `backend/tests/unit/distill/test_value_objects.py`, `backend/tests/unit/distill/test_regeneration_policy.py`

**Intent**: Pin pass line, rank order, tier selection at boundaries, zero-proposal regeneration, and malformed tiers refused.

**Contract**: flat tests; module-private `_policy()` factory.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/test_value_objects.py tests/unit/distill/test_regeneration_policy.py -v` passes

---

## Phase 3: Minting a round on the run

### Overview
Candidates enter the run through the deterministic gates.

### Changes Required:

#### 1. Round minting and read-back
**File**: `backend/src/domain/distill/run.py`

**Intent**: Turn a phase's proposals into tracked candidates, with gate discards set on the way in and unmintable proposals kept as candidates without a card.

**Contract**:
- `add_round(round, proposals, card_factory)` appends one `Candidate` per proposal in order; refs continue the run's sequence (`c1`, `c2`, … across rounds). For each proposal it builds `CardSide`/`Anchor`, resolves the anchor with `document.locate`, and mints via `card_factory` for `note.id`; a `CoreException` from building the value objects yields `card=None`.
- `of_round(round)`, `awaiting_review(round)` — replace `NotImplementedError`.
- `Candidate.awaits_review` — card present, no discard, no verdict.
- `Candidate.failure` — for this phase: gate discard reason (with detail when present) or `could not become a card`; `None` while standing.
- `cards()` — every candidate's non-`None` card, in candidate order.

**File**: `backend/tests/unit/distill/test_distill_run_minting.py`

**Intent**: Pin ordering and ref continuity across rounds, grounded vs ungrounded vs oversized gating, unmintable kept with `card=None` and excluded from `cards()`, and what awaits review.

**Contract**: module-private `_run(content: str)` factory building `Note`, `NoteDocument`, and a default `RegenerationPolicy`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/test_distill_run_minting.py -v` passes

---

## Phase 4: Review verdicts, share, and gaps on the run

### Overview
What a review applies and what regeneration is fed.

### Changes Required:

#### 1. Verdicts and first-round queries
**File**: `backend/src/domain/distill/run.py`

**Intent**: Record review judgments per candidate with the domain deciding pass/fail, and derive whether and what to regenerate.

**Contract**:
- `record_verdicts(round, verdicts)` — for candidates awaiting review in `round`: set the verdict its ref names; unknown refs and refs of other rounds are ignored; a non-passing grade discards the card `LOW_QUALITY` with `reasoning` as detail; a candidate left without a verdict is discarded `LOW_QUALITY` with detail `no verdict`.
- `Candidate.accepted` — verdict present, passes, card not discarded.
- `Candidate.failure` extended — review reasoning for `LOW_QUALITY`.
- `regeneration_needed()` — `policy.regenerate(note.content, accepted, proposed)` over first-round candidates, `proposed` counting all of them.
- `gaps()` — first-round candidates whose `failure` is not `None`.
- `accepted_example()` — the first accepted first-round candidate, or `None`.

**File**: `backend/tests/unit/distill/test_distill_run_review.py`

**Intent**: Pin pass vs low-quality discard with reasoning, unknown-ref and missing-verdict handling, replacement review never touching first-round verdicts, share counting gate losses, and gaps/example.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/test_distill_run_review.py -v` passes

---

## Phase 5: Merge on the run

### Overview
Duplicate removal with the domain's survivor rule.

### Changes Required:

#### 1. Merge pool and duplicate discard
**File**: `backend/src/domain/distill/run.py`

**Intent**: Keep one card per duplicate group by grade, round and proposal order, discarding the rest as duplicates.

**Contract**:
- `merge_pool()` — accepted candidates of either round, in candidate order.
- `discard_duplicates(groups)` — per group, members restricted to `merge_pool` (unknown or non-pool refs ignored; a group left with fewer than two members is a no-op); survivor = highest `grade.rank`, then `REPLACEMENT` over `FIRST`, then earliest ref; others discarded `DUPLICATE` with the group's `reasoning` as detail.

**File**: `backend/tests/unit/distill/test_distill_run_merge.py`

**Intent**: Pin better-grade survival, replacement-wins tie, same-round earlier-wins tie, non-pool refs untouched.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/test_distill_run_merge.py -v` passes

---

## Phase 6: Distill instruction builders

### Overview
What each phase tells the model, as domain prose with required blocks enforced.

### Changes Required:

#### 1. Base and phase builders
**File**: `backend/src/domain/distill/instructions.py`

**Intent**: Compose the general floor (`FLOW`, `LANGUAGE`) with each phase's blocks so the advertised required set and the built instruction cannot disagree.

**Contract**:
- `DistillInstructionBuilder.required` = `{FLOW, LANGUAGE} | phase_required`; `build` = general blocks then `phase_blocks`, as `Instruction(blocks, required)`.
- Generating: `TASK` (propose grounded question/answer cards, each quoting the note verbatim; how many is the model's call), `NOTE`.
- Reviewing(round): `TASK` (grade each candidate on the four-grade scale with reasoning, by ref), `NOTE`, `CANDIDATES` — `awaiting_review(round)` rendered one per ref.
- Regenerating: `TASK`, `NOTE`, `GAPS` — each gap with its `failure`, or an explicit "no usable cards; propose cards outright" when there are none; `ACCEPTED_EXAMPLE` only when `accepted_example()` is not `None`.
- Merging: `TASK` (group candidates that say the same thing, with reasoning), `CANDIDATES` — `merge_pool()` by ref.
- No block names the output schema or a grade's pass line.

**File**: `backend/tests/unit/distill/test_distill_instructions.py`

**Intent**: Pin required sets per builder, general-before-phase ordering, candidates rendered under refs for the round judged, `GAPS` with failures and the empty-gap wording, and `ACCEPTED_EXAMPLE` conditional presence.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/test_distill_instructions.py -v` passes

---

## Phase 7: Distill machine wiring and route

### Overview
The graph becomes walkable, and both routes are proven without a model (FR-04).

### Changes Required:

#### 1. Machine hooks and model-free answers
**File**: `backend/src/domain/distill/flow.py`

**Intent**: Wire the machine to the run and let empty phases answer without a model.

**Contract**:
- `DistillMachine.current_state` returns the graph's state for the run's phase (cast narrowed); `state_name_of` reads `run.phase`; `enter_state` writes it; `build_instruction` returns `current_state.instruction_builder.build(run)`.
- `output_without_model`: `Generating`/`Regenerating` → `None`; `Reviewing` → `CardsReviewed(verdicts=[])` when `awaiting_review(FIRST)` is empty, else `None`; `ReviewingReplacements` likewise for `REPLACEMENT`; `Merging` → `DuplicatesFound(groups=[])` when `merge_pool()` has fewer than two, else `None`.

**File**: `backend/tests/unit/distill/test_distill_flow.py`

**Intent**: Pin graph shape (terminal `{MERGING}`, no state reaches itself, every state is a `StructuredState`), guard exclusivity on above/below-threshold runs, and scripted walks — the loop from the machine docstring with hand-built events — ending in `MERGING` via the direct and the regenerating route, with `advance` refusing at the end.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/test_distill_flow.py -v` passes
- `cd backend && uv run basedpyright src/domain` reports 0 errors

---

## Phase 8: Deterministic structured task adapter

### Overview
The in-memory adapter for `StructuredTaskPort`, thin, driving off the domain's declarations.

### Changes Required:

#### 1. Adapter
**File**: `backend/src/adapters/out/in_memory/distill/structured_task.py`

**Intent**: Fabricate schema-valid results keyed on the output type, keeping today's generation shape so BDD stays meaningful.

**Contract**: `DeterministicStructuredTaskAdapter.complete(instruction, output)`:
- `CardsProposed` with a `GAPS` block present → no proposals.
- `CardsProposed` otherwise → one proposal per paragraph block of the `NOTE` block's note text (front/back split at first sentence end, quote = block) plus the fabricated ungrounded control proposal — the logic moved from `card_generation.py`. The note text must be recoverable from the `NOTE` block verbatim; Phase 6's `NOTE` block carries it as the block's whole text.
- `CardsReviewed` → `SOUND` for every ref listed in `CANDIDATES`, reasoning a fixed literal.
- `DuplicatesFound` → no groups.
- Any other output type → `TypeError`.

**File**: `backend/tests/unit/distill/contracts/test_structured_task_port_contract.py`

**Intent**: One behavioural contract for the port, parametrized `_IMPLEMENTATIONS` (`ids=["deterministic"]`): each answer validates as the requested output type, generation is deterministic for the same instruction, a review names only refs from the instruction.

**File**: `backend/tests/unit/distill/test_deterministic_structured_task.py`

**Intent**: Pin the deterministic specifics: control card present, empty proposals under `GAPS`, all-`SOUND` verdicts, no groups.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/contracts/test_structured_task_port_contract.py tests/unit/distill/test_deterministic_structured_task.py -v` passes

---

## Phase 9: Command walks the flow; old seam removed

### Overview
`GenerateCardsCommand` runs the loop; composition and test support move to the new port; the single-shot seam goes.

### Changes Required:

#### 1. Command
**File**: `backend/src/application/distill/commands/generate_cards.py`

**Intent**: Walk the distill machine without deciding a route, then persist once.

**Contract**: `GenerateCardsCommand(uow_factory, structured_task: StructuredTaskPort, card_factory: CardFactory, regeneration_policy: RegenerationPolicy)`. `handle(note_id)`: keep the not-found and redelivery no-ops; build `DistillRun(note, NoteDocument.of(note.content), policy)` and `DistillMachine(run, deps)` (a module-private deps object exposing `card_factory`); loop: `result = state.output_without_model(run)` or `await port.complete(machine.build_instruction(), state.output)`, `await machine.apply(result)`, stop when `await machine.advance()` is `False`. If the port raised, or the stop phase is not terminal (`graph.is_terminal`): log, `note.mark_failed()`, save, commit, nothing else persisted. Otherwise save every `run.cards()`, `note.mark_ready()`, save, commit.

#### 2. Seam swap
**Files**: `backend/src/adapters/compose.py`, `backend/tests/integration/support/in_memory_distill.py`, `backend/src/application/distill/ports.py`, `backend/src/application/distill/value_objects.py`, `backend/src/adapters/out/in_memory/distill/card_generation.py`, `backend/tests/unit/distill/contracts/test_card_generation_contract.py`, `backend/tests/unit/distill/test_flashcard_gen_handler.py`

**Intent**: Wire the deterministic structured task adapter and a `RegenerationPolicy` (tiers ≤1500: 0.5, ≤6000: 0.6, open: 0.7 — compose reads them from settings only in Phase 11, a module constant until then); delete `CardGeneration`, `DeterministicCardGenerationAdapter`, its contract suite, and the `application.distill.value_objects` re-export, moving imports to `domain.distill.value_objects.CardProposal`.

**Contract**: `InMemoryDistillComposition.structured_task: DeterministicStructuredTaskAdapter` replaces `card_generation`; `regeneration_policy` field added. No remaining reference to `CardGeneration` under `backend/`.

**File**: `backend/tests/unit/distill/test_generate_cards_command.py`

**Intent**: Rewrite against the new constructor with a module-private `_ScriptedStructuredTask` for states the deterministic adapter cannot reach: live and discarded cards persisted with READY; zero surviving cards still READY; a port raising mid-flow leaves FAILED with no card saved; not-found and redelivery stay no-ops.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill -v` passes
- `cd backend && uv run pytest tests/bdd -m distill-flow -v` passes
- `cd backend && uv run pytest tests/integration -v` passes
- `cd backend && uv run python -c "import adapters.compose"` exits 0
- `grep -rn "CardGeneration" backend/src backend/tests` returns nothing

---

## Phase 10: pydantic-ai structured task adapter

### Overview
The real-provider adapter, rendering the domain's instruction and output, traced per call.

### Changes Required:

#### 1. Adapter
**File**: `backend/src/adapters/out/llm/distill/structured_task.py` (plus `__init__.py`)

**Intent**: Send one structured request per call and return the validated result, with no dispatch on phase.

**Contract**: `PydanticAiStructuredTaskAdapter(agent: Agent, model_name: str)`; `complete(instruction, output)` opens `observation(<snake_case of output.__name__>, observation_type="generation", input_value=[block.text for block in instruction.blocks])`, records the model name, runs `agent.run(instructions=[block.text …], output_type=output)`, records usage (`input`/`output` tokens) and the output's JSON, returns `result.output`. Exceptions propagate unchanged; no retry policy of its own.

**File**: `backend/tests/unit/distill/test_pydantic_ai_structured_task.py`

**Intent**: With `models.ALLOW_MODEL_REQUESTS = False`, `TestModel`/`FunctionModel` and an in-memory span exporter: a result of the requested type is returned for each output; instruction block texts reach the model as instructions; the span is named from the output with model and usage recorded; a model error propagates and marks the span errored.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/test_pydantic_ai_structured_task.py -v` passes
- `cd backend && uv run basedpyright src/adapters` reports 0 errors

---

## Phase 11: Live composition and run tracing

### Overview
Select the provider by settings, group each run's calls under one Langfuse session, and verify end to end against a real provider (FR-08).

### Changes Required:

#### 1. Settings
**File**: `backend/src/config/settings.py`, `backend/.env.example`

**Intent**: Make provider, model and threshold tiers configurable.

**Contract**: `DistillTaskProvider(StrEnum)` {`deterministic`, `pydantic_ai`}; `distill_task_provider: DistillTaskProvider = PYDANTIC_AI`; `distill_model: str = "openai/gpt-4o-mini"`; `distill_regeneration_tiers: list[tuple[int | None, float]] = [(1500, 0.5), (6000, 0.6), (None, 0.7)]` (JSON from env). Settings imports no domain type.

#### 2. Composition
**File**: `backend/src/adapters/compose.py`

**Intent**: Build the structured task port by provider, mirroring `_build_capture_agent_port`, and the policy from settings.

**Contract**: `_build_structured_task_port(settings) -> StructuredTaskPort` with lazy pydantic-ai imports; `RegenerationPolicy(tiers=…)` built from `distill_regeneration_tiers`.

#### 3. Run span
**File**: `backend/src/adapters/out/worker/handlers/flashcard_gen.py`

**Intent**: Group one run's model calls in Langfuse without the domain supplying anything.

**Contract**: `handle` wraps `command.handle` in `observation("distill_run", observation_type="chain", input_value={"note_id": …}, session_id=str(note_id))`.

**File**: `backend/tests/unit/distill/test_flashcard_gen_handler.py`, `backend/tests/unit/test_settings.py`

**Intent**: Pin that the handler exports a `distill_run` span carrying the note id as session with command spans nested under it, and the settings defaults and env parsing of tiers.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest -v` passes (full suite)
- `cd backend && uv run basedpyright` reports 0 errors
- `cd backend && uv run ruff check src tests` is clean

#### Manual Verification:
- With `DISTILL_TASK_PROVIDER=pydantic_ai`, `OPENROUTER_API_KEY` and Langfuse keys set, start the backend, run a capture session to an approved note, let the outbox worker drain, then `curl` the note's cards: note `ready`, live cards grounded in the note, any discards carrying one of the four reasons.
- In Langfuse, the run shows one `distill_run` trace under session = note id, with child spans `cards_proposed`, `cards_reviewed` (and, when regeneration happened, the second pair) and `duplicates_found` when the pool held two or more cards, each with model and token usage.
- Repeat with a one-sentence note: note ends `ready` even with zero live cards.

---

## Testing Strategy

### Unit Tests:
- Shared mechanic: `advance` outcomes on the existing test graph.
- Domain: grade/policy rules; `DistillRun` minting, review, merge; builders; graph shape and model-free walks.
- Adapters: deterministic port contract and specifics; pydantic-ai adapter via `TestModel`/`FunctionModel`; handler span.
- Application: command persistence, empty outcome, failure, no-ops.

### Integration Tests:
- Existing `tests/integration` suites over `InMemoryDistillComposition`; BDD `distill-flow` AC-03..AC-06 stay green unchanged.

### Manual Testing Steps:
- Phase 11 live run and Langfuse inspection.

## Performance Considerations

A run makes 3–5 model calls instead of one (generate, review, optional regenerate and review, merge); empty review and sub-two merge phases skip the call. Acceptable for a background outbox job; no parallelism introduced.

## Migration Notes

In-memory only; nothing persisted changes shape beyond two new `DiscardReason` values already on disk. New env keys have defaults.

## References

- Frame: `context/changes/llm-adapter-distill-live/frame.md`, `frame-log.md`
- Contract session: `context/changes/llm-adapter-distill-live/discover-contracts-log.md`
- Effort: `context/efforts/llm-adapter/frame.md` (FR-04, FR-05, FR-08, FR-09), `roadmap.md` S-06, `research-pydantic-ai.md`, `research-langfuse.md`
- Rules: `context/foundation/rules/layering.md`, `contract-testing.md`, `cqrs-lite.md`; `context/foundation/testing-conventions.md`
- Precedent adapter: `backend/src/adapters/out/llm/capture/agent.py`
