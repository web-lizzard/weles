## Current State

Session closed on 2026-09-13. The contract is modelled; the remaining questions are `/plan`'s.

**Verified at close:** `ruff check`/`ruff format` clean over `src/domain` and
`src/application`; `basedpyright` 0 errors and 0 warnings (stub parameters
marked `_ = …`, as capture does); `adapters.compose` imports; distill graph `terminal_states == {MERGING}`, no
state reaches itself; `tests/unit/distill` 87 passed.

**Shared mechanics (`domain/shared/graph/`).**
- `model.py` — `StructuredState(State)`: abstract `output -> type[EventT]` (the phase's
  structured result, which is also the event applied) and
  `output_without_model(context) -> EventT | None` (a result the phase knows without a
  call). `Graph` unchanged; capture unaffected.
- `machine.py` — `StateMachine.advance() -> bool`: one guard-selected move; refuses on no
  passing guard, terminal state, or more than one passing guard. `available_transitions`
  kept. `StructuredStateMachine` narrows `current_state`; its docstring is the command loop.

**Command loop (not yet written into `GenerateCardsCommand`).** Build `DistillRun` →
`DistillMachine(run, deps)` → repeat: result = `current_state.output_without_model(run)` or
`port.complete(build_instruction(), current_state.output)`; `apply(result)`; stop when
`advance()` refuses → finished iff `graph.is_terminal(current_state_name)`, else mark the
note failed → persist `run.cards()` → note READY (also with zero surviving cards). No
dispatcher; the command holds no route.

**Distill (`domain/distill/`).**
- `value_objects.py` — `DiscardReason.LOW_QUALITY`/`DUPLICATE`, `DistillPhase`,
  `CardProposal` (raw strings, moved from application), `CandidateRef`, `ReviewGrade`
  (POOR < WEAK < SOUND < STRONG, `rank`, `passes`), `CardVerdict`, `DuplicateGroup`.
- `regeneration.py` — `ThresholdTier`, `RegenerationPolicy.regenerate(content, accepted,
  proposed)`; zero proposed regenerates.
- `run.py` — `CandidateRound`, `Candidate`, `DistillRun` with mutators (`add_round`,
  `record_verdicts`, `discard_duplicates`) and queries; outputs-as-events `CardsProposed`,
  `CardsReviewed`, `DuplicatesFound`, union `DistillEvent`.
- `deps.py` — `DistillDeps` (card factory).
- `instructions.py` — block names and builders; one reviewing builder for both reviews.
- `flow.py` — `DistillMachine`, five states, guards and actions delegating to the run,
  `_DISTILL_GRAPH` G→R, R→RG | R→M, RG→RR, RR→M.
- `ports.py` — `StructuredTaskPort.complete(instruction, output)`.
- `application/distill/value_objects.py` re-exports `CardProposal`.

**Carried to `/plan`.**
1. `verdict-coverage` — review answer that omits or invents refs (proposal: ignore unknown
   refs, discard unjudged as `LOW_QUALITY` with "no verdict").
2. `merge-tie-same-round` — equal grades within one round (proposal: earlier proposal
   survives).
3. `unmintable-proposal` — empty/identical sides: count in share, not persisted, replaced
   with "could not become a card" — unconfirmed.
4. `grade-scale` — names and pass line (written: pass from SOUND).
5. Unwritten surfaces: `GenerateCardsCommand` constructor and loop (breaks `compose.py` and
   `tests/unit/distill` when changed), deterministic and pydantic-ai adapters for
   `StructuredTaskPort` (span named from `output`), the worker handler's parent span with
   `note_id` as Langfuse session, settings for threshold tiers, removal of the application
   re-export, all stub bodies and prose.
6. Roadmap S-06 prose ("single-shot", "without a transition graph") is stale — `/roadmap`'s.

**Split out.** Capture's command walking its graph with `advance` is change
`capture-command-graph-walk`; its `change.md` notes were corrected this session.

## Log

### 2026-09-12 — structured-output-slot: How a state declares its structured output — OPEN

Why: every distill phase returns one typed result, and `State` (`domain/shared/graph/model.py:87-145`)
has no slot for its schema. Options: a `StructuredState` subclass in shared (typing needs
the machine or graph to know the narrower state type; Python 3.12 has no TypeVar
defaults, so a new `Graph` parameter would reach capture too); an optional
`output: type[EventT] | None` on the base `State` (capture returns `None`); or one
mandatory output `Tool` per phase (reuses `Tool.result`, but needs a "must call" flag and
parses an opaque `ToolArguments` bag for a schema pydantic already has).

### 2026-09-12 — guard-decided-move: The machine, not the command, picks the next phase — OPEN

Why: frame requires the application not to decide the route, yet `transition(target)`
(`domain/shared/graph/machine.py:84-105`) makes the caller name the target. A single move
chosen by passing guards keeps routing in the domain. Unsettled: behaviour when no guard
or more than one passes, given the accepted rule that the graph raises no exceptions of
its own (capture-modes log `graph-exceptions`).

### 2026-09-12 — output-is-event: A phase's structured output is the event it applies — OPEN

Why: removes an adapter-side translation table like `_event_from_tool_result`
(`adapters/out/llm/capture/agent.py:236-255`). Diverges from capture's separate
vocabularies, whose stated reason (a tool result re-enters the model's context) does not
hold for a final structured output.

### 2026-09-12 — model-port-shape: One generic structured-task port vs per-task ports — OPEN

Why: user asked for either several adapters or one dispatching by state. With schema and
instruction both declared by the state, a single `complete(instruction, output)` port
needs no dispatch at all; per-task ports (generate/review/merge) duplicate the
declaration the state already holds. The deterministic adapter is the cost: it must
fabricate outputs by output type.

### 2026-09-12 — empty-phase: A phase with nothing to judge — OPEN

Why: a first round fully lost at the gates leaves REVIEWING nothing to review; a
regeneration yielding no replacement leaves REVIEWING_REPLACEMENTS empty; MERGING with
fewer than two accepted cards cannot find duplicates. Either extra guarded edges (graph
grows, MERGING still needs an in-state skip because it is terminal) or a state-level
"has work" predicate.

### 2026-09-12 — discard-reasons-on-disk: `LOW_QUALITY`, `DUPLICATE` and `DistillPhase` written — ACCEPTED

Why: frame-settled (`discard-reasons`, `review-phase-reuse`, `acyclic-flow` in
`frame-log.md`). `DistillPhase` is separate from `DistillationStatus`, which is the
note's persisted status, not the run's phase.

### 2026-09-12 — graph-dispatcher: A domain dispatcher walks the graph; the command does not know the route — ACCEPTED

Why: user decision — the handler should not know distill's route. `GraphDispatcher` in
`domain/shared/graph/dispatcher.py` holds the machine and the model-facing port and steps
until `advance` refuses. The machine itself still holds no port, keeping capture-modes'
`agent-port` rule true; the port is a domain port, so a domain service holding it is within
`layering.md`. `Graph` needed no change.
Consequence: the distill command shrinks to build context → `run()` → persist from
`machine.context`; a `False` from `run` is a failed run.

### 2026-09-12 — guard-decided-move: `advance` takes the one guard-selected move — ACCEPTED

Why: user agreed; keeps routing in the domain. Ambiguity (more than one passing guard) is a
refusal, not an exception, honouring capture-modes' `graph-exceptions`; guard exclusivity
is pinned by the composition's suite. `available_transitions` stays at the user's request
as the "what is permitted now" query.
Supersedes: 2026-09-12 guard-decided-move OPEN.

### 2026-09-12 — next-move-query: A separate `next_move` query beside `advance` — REJECTED

Why: user asked whether `advance` suffices. It does: the query's only reader would be
`advance`, and a route is pinned in tests by advancing a context and reading its phase.
Removed from `machine.py`.

### 2026-09-12 — output-is-event: A phase's structured output is the event it applies — ACCEPTED

Why: user agreed. Capture's split between tool results and events rests on a tool result
re-entering the model's context; a final structured output never does.
Supersedes: 2026-09-12 output-is-event OPEN.

### 2026-09-12 — model-port-shape: One phase-agnostic `StructuredTaskPort` — ACCEPTED

Why: user's "brzmi ok" on the adapter point (interpretation stated back to the user). The
state declares instruction and output, so the adapter has nothing to dispatch on; the
deterministic adapter keys fabricated results on the output type. Placed in
`domain/shared/graph/ports.py` because the shared dispatcher consumes it.
Supersedes: 2026-09-12 model-port-shape OPEN.

### 2026-09-12 — structured-output-slot: `StructuredState` subclass written as the proposal — OPEN

Why: written so the typing could be checked rather than argued: `basedpyright` is clean
with `StructuredStateMachine` narrowing `current_state` and `Graph` unchanged, so the
subclass costs capture nothing. Awaiting user confirmation.

### 2026-09-12 — capture-advance-adoption: Capture's command walks its graph with `advance` too — OPEN

Why: user suggestion. Outside this change's frame boundaries (distill only), and it would
change behaviour: `_dispatch` (`application/capture/commands/send_message.py:145-162`)
never returns to conversing within one turn, whereas looping `advance` would. Capture
streams to HTTP, so `GraphDispatcher.run() -> bool` does not serve it without a streaming
variant.

### 2026-09-12 — capture-advance-adoption: Capture's graph walk gets its own change — PARKED

Why: user decision, so the idea is not lost while staying out of this change's frame.
Opened `context/changes/capture-command-graph-walk/` (`origin: llm-adapter-distill-live`)
carrying the caveats: drafting→conversing re-entry within one turn, the streaming mismatch
with `GraphDispatcher.run() -> bool`, and the dependency on `advance` landing here first.
Supersedes: 2026-09-12 capture-advance-adoption OPEN.

### 2026-09-12 — structured-output-slot: `StructuredState` subclass declares the output — ACCEPTED

Why: user confirmed ("jasna sprawa"). Type-checks with `Graph` and capture untouched.
Supersedes: 2026-09-12 structured-output-slot OPEN.

### 2026-09-12 — graph-dispatcher: No domain dispatcher; the command loops over `advance` — REJECTED

Why: user's point — once `advance` selects the move, the command's loop picks no step, so
it holds no route and a dispatcher adds a class without adding a guarantee. Also matches
capture-modes' `agent-port` (the command holds the model port) and the streaming mismatch
noted for capture: a shared non-streaming `run()` would have had one consumer.
`StructuredStateMachine` moved into `machine.py`; `dispatcher.py` deleted.
Supersedes: 2026-09-12 graph-dispatcher ACCEPTED.

### 2026-09-12 — model-port-shape: `StructuredTaskPort` moves to `domain/distill/ports.py` — ACCEPTED

Why: its only shared consumer was the dispatcher; with the command as the sole holder it
sits beside distill's other ports, as `CaptureAgentPort` sits in capture's. Its shape is
unchanged and still phase-agnostic, so promoting it to shared later is a move, not a
redesign. `domain/shared/graph/ports.py` deleted.

### 2026-09-12 — port-task-argument: `complete` takes no `task` name — REJECTED

Why: user asked what `task` is for; its only reader was tracing, and tracing does not need
it from the domain. The adapter names its span from `output`, and one run's calls group
under a parent span the worker handler (`adapters/out/worker/handlers/flashcard_gen.py`,
already an adapter) opens around the command, the way capture's adapter attaches
`session_id` (`adapters/out/llm/capture/agent.py:73-78`). Caveat: if both review phases
share one output type, their spans share a name and are told apart only by order within the
parent span.

### 2026-09-12 — empty-phase: A phase with nothing to judge answers without a model — OPEN

Why: user proposed merge as a no-op when there is nothing to merge. A no-op still needs
the loop to know not to call the model, so it is written as a determined result rather
than a skip flag: `StructuredState.output_without_model` returns the event the phase would
get anyway (no duplicates), the command applies it as it would a model's, and actions and
`advance` see a uniform context. Chosen over extra guarded edges (graph grows; terminal
MERGING could not use one) and over a bare `has_work` bool (a skipped phase would apply
nothing, so "entered a phase" would stop implying "a result was applied"). Open: whether
both reviews use the same hook for an empty candidate set, and the zero-proposal round.
Supersedes: 2026-09-12 empty-phase OPEN (options only).

### 2026-09-13 — empty-phase: Empty reviews answer an empty verdict list — ACCEPTED

Why: user decision. Both review phases and merge use `output_without_model`; generation
phases always ask the model.
Supersedes: 2026-09-12 empty-phase OPEN.

### 2026-09-13 — zero-proposal-round: A round with no proposals is below threshold — ACCEPTED

Why: user decision. `RegenerationPolicy.regenerate` treats zero proposed as below any
threshold; regeneration's required `GAPS` block then asks for cards outright.

### 2026-09-13 — distill-composition: Run, outputs, policy, states and graph written — ACCEPTED

Why: follows every settled frame and session decision. Candidates are addressed by
run-minted `CandidateRef`, not `CardId`, to keep what the model echoes short. The
threshold policy rides on the run because guards read only the context
(`EdgeCondition`, `domain/shared/graph/model.py:20`). `CardProposal` moved to the domain
since domain actions consume it; application re-exports it so no test import changes in
this session. Graph checked: terminal `{MERGING}`, acyclic.

### 2026-09-13 — verdict-coverage: A review answer that misses or invents refs — OPEN

Why: the output schema cannot know the run's refs, so a model can omit a candidate or name
one that does not exist; the domain has to decide what an unjudged card becomes.

### 2026-09-13 — merge-tie-same-round: Equal grades within one round — OPEN

Why: the frame's tie rule separates only a replacement from a first-round card.

### 2026-09-13 — unmintable-proposal: Proposals that cannot become a card — OPEN

Why: empty or identical sides raise in `CardFactory.mint` today and are skipped
(`application/distill/commands/generate_cards.py:64-68`). Written as counting toward the
share, not persisted, and replaced with a "could not become a card" failure — unconfirmed.

### 2026-09-13 — grade-scale: Review grade names and pass line — OPEN

Why: written as POOR < WEAK < SOUND < STRONG, passing from SOUND; a proposal, not a
decision.

### 2026-09-13 — actions-mutate-run: Actions and guards delegate to `DistillRun` — ACCEPTED

Why: user's point that actions should change the run. They were already attached to their
states (`State.actions`, default `get_actions` runs the whole inventory) but had nothing on
the run to call. `DistillRun` gains `add_round`, `record_verdicts`, `discard_duplicates`
(stubs); actions narrow the event and call one mutator, guards return the run's query —
the same split as capture, where actions call `CaptureSession` methods
(`domain/capture/graph.py:329-351`). Flow wiring is now code; card and discard logic stays
on the run, unwritten.

### 2026-09-13 — open-questions-to-plan: Verdict coverage, same-round tie, unmintable proposals, grade scale go to `/plan` — PARKED

Why: user closed the session ("chyba nie mamy już co modelować"); each question fixes a
rule inside an already-declared method (`record_verdicts`, `discard_duplicates`,
`add_round`, `ReviewGrade.passes`), so none changes a signature.
