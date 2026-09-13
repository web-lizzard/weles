# Graph state machines

`backend/src/domain/shared/graph/` — the shared mechanism behind every multi-turn
domain flow. No ADR backs this yet; it emerged from `domain/capture/graph.py`
(the first concrete composition) and was reused, unchanged, by
`domain/distill/flow.py`. Treat this doc as the rationale until one is written.

## Why a shared mechanism

Capture and distill are both "a context sits in one of several phases across
many turns, moves between phases on rules, and does phase-specific work on
entry/exit and per event." Without a shared mechanism, each flow reinvents its
own phase enum, its own dispatch-by-phase `if`/`match`, and its own place to
decide "can this flow move on now." `domain/shared/graph/` factors that
mechanism out once, generic over the aggregate it carries (`ContextT`), the
collaborators an action may reach for (`DepsT`), the event a turn feeds it
(`EventT`), and the enum naming its states (`NameT: StrEnum`). A concrete flow
supplies only a `Graph` and two hooks (`state_name_of`, `enter_state`) —
everything else is inherited mechanics from `StateMachine`.

## Core vocabulary (`domain/shared/graph/model.py`)

- **`State[ContextT, DepsT, EventT]`** — one node: what it offers (`tools`),
  what it can do (`actions`), how it builds this turn's instruction
  (`instruction_builder`), and what a routing model reads about it
  (`description`). `get_tools`/`get_actions` are *methods over the whole
  phase*, not per-item predicates — a phase may withhold one tool because
  another already did its work, or run one action instead of another
  depending on which event arrived. That eligibility is a statement about the
  phase as a whole, which independent predicates can't express.
- **`StructuredState[ContextT, DepsT, EventT]`** — a `State` whose model
  answers once with one typed result (`output`) instead of conversing through
  tools. Adds `output_without_model(context) -> EventT | None`: the answer a
  phase already knows without asking a model (an empty review, a merge over
  fewer than two cards) — abstract, not defaulted, so a phase that always
  needs the model says `None` on purpose.
- **`Tool[ContextT, ResultT: ToolResult]`** — the model-facing surface of a
  conversational state: `name`, `description`, `result` (a `ToolResult`
  subclass pinning a `Literal` discriminator matching `name`), and `handler`
  (reads context + arguments, computes, never mutates, never persists).
- **`Transition[ContextT, DepsT, EventT]`** — one edge: an optional `guard`
  (`EdgeCondition`, reads only the context) and `actions` (`EdgeAction`,
  run when the edge is taken). Carries no source/target — those are the keys
  it sits under in the graph, so an edge can't claim endpoints it isn't filed
  under.
- **`Graph[ContextT, DepsT, EventT, NameT]`** — `states` by name and
  `transitions` by source then target, as one static, declared-whole value
  that never reads a context. Keying rather than listing makes "two states
  can't share a name" and "two edges can't share a source/target pair"
  structural instead of tested. `is_terminal(name)` / `terminal_states`: a
  state with no outgoing edge at all — *structurally* terminal only; an edge
  whose guard can never pass is just as inescapable but isn't reported here,
  because no static reading of a graph can distinguish "unsatisfiable" from
  "not yet satisfied."

## The machine (`domain/shared/graph/machine.py`)

`StateMachine[ContextT, DepsT, EventT, NameT]` holds a `context` and `deps`
and knows nothing about any particular flow.

- **`apply(event)`** — runs the current state's actions for this event.
  Crosses no edge; a move is a separate, explicit act.
- **`available_transitions()`** — every target reachable from the current
  state whose guard passes, mapped to its description. Answers "what is
  permitted now."
- **`advance()`** — takes the one move guards select, through `transition`.
  Refuses (`False`) when the state is terminal, when no guard passes, and
  when *more than one* guard passes — the last is a mistake in the
  declaration (guards meant to be mutually exclusive weren't), not a runtime
  condition, and the machine refuses rather than guesses. Answers "where does
  the flow go" and goes there in the same act — there is no separate query
  for the selected target, because a test pins a route by advancing a context
  and reading its phase back off it.
- **`transition(target)`** — takes one named edge: runs its actions, then
  writes the new state name onto the context via `enter_state`. A target the
  current state doesn't reach *directly* is refused even if the graph could
  reach it in two moves — crossing a phase without a turn in it would skip
  that phase's own actions.

A concrete machine implements three hooks: `graph` (the same value every
time), `state_name_of(context)` (read the phase off the aggregate — the
aggregate is the only durable carrier, the machine keeps no copy), and
`enter_state(context, name)` (write it back, in memory only).
`StructuredStateMachine` narrows `current_state` to `StructuredState` and
adds `build_instruction()`.

## Two flavors in this codebase

- **Conversational** (`domain/capture/graph.py`, `CaptureMachine` — the
  original composition): states offer tools across many turns of the same
  phase; a state's `get_tools`/`get_actions` narrow as prior turns do their
  work (e.g. `Conversing` withdraws `propose_session_topic` once the session
  already has one). The graph cycles — `CONVERSING ⇄ DRAFTING` — because a
  return-to-conversation intent is a legitimate move backwards, guarded so it
  can't loop forever on nothing (`conversation_requested`, consumed
  single-use by the edge action).
- **Structured, single-shot** (`domain/distill/flow.py`, `DistillMachine`):
  every state answers once, in its declared `output`, never through tools —
  `tools` is `()` and `description` is `""` on every state, because guards
  alone route and nothing narrates the graph to a model. The graph is
  acyclic and has exactly one terminal state (`MERGING`); regeneration
  happens at most once because no edge leads back to it, not because
  anything counts a visit.

Both share the same `apply`/`advance`/`transition` mechanics and the same
`Graph`/`Transition` declaration shape. Building a third flow means picking
one of these two shapes (conversational-with-tools or
structured-single-shot), not inventing a third state/machine pair.

## Walking a structured flow (the command's loop)

`StructuredStateMachine` holds no model-facing port — the application command
owns the iterator:

```python
while True:
    state = machine.current_state
    result = state.output_without_model(context) or await port.complete(
        machine.build_instruction(), state.output
    )
    await machine.apply(result)
    if not await machine.advance():
        break
```

`output_without_model` is tried first so a phase with nothing to judge (no
candidates awaiting review, fewer than two cards to merge) never pays for a
model call — the model is asked only when the phase actually needs it, but
either way `apply` runs the same actions and `advance` sees the same
resulting context. The loop is identical for any structured flow; see
`application/distill/commands/generate_cards.py` for the concrete instance,
including how a stop outside a terminal state (or a raised model call) is
told apart from a normal finish.

## Instruction building

A `StructuredState`/conversational `State` declares `instruction_builder:
InstructionBuilder[ContextT]` (`domain/shared/instruction/model.py`):
`build(context) -> Instruction`, synchronous and reaching nothing — an
instruction describes the turn as it stands, never enriched by a fetch. An
`Instruction` is an ordered tuple of named `InstructionBlock`s plus the
`required` names that must be among them, validated at construction (no
duplicate name, nothing required missing) so an incomplete instruction has no
construction path, not just a guard a dispatcher remembers to call. A block
never names a tool: a tool reaches the model through the provider's own tool
channel, so a block claiming to gate one would be lying about what withholding
it does.

## Invariants pinned by tests, not by types

`tests/unit/shared/test_graph_machine.py` is the one contract suite for the
mechanism (`context/foundation/rules/contract-testing.md` applies: run on
every CI invocation). What it pins that the type system can't:

- A composition's guards are mutually exclusive for every reachable context —
  `advance` only *detects* the violation (refuses on >1 passing guard); the
  composition's own suite has to prove it never happens in practice.
- A graph's states are keyed uniquely and every transition endpoint names a
  declared state (structural, but still worth a fixture-level check when a
  graph is hand-built).
- The four `advance` outcomes (terminal, no guard, one guard, >1 guards) on
  the shared test graph fixtures.

## When to reach for this

Use `domain/shared/graph/` when a domain concept is "many turns, a small
closed set of named phases, phase-specific work on entry/exit or per event,
and rules (not caller choice) decide when it moves." Don't reach for it for a
single request/response command with no phase concept — that's a plain
application command, no graph needed.
