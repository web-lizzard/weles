---
status: closed
created: 2026-09-12
updated: 2026-09-12
---

## Boundaries

**In scope.**

The legal phases of a capture session, and the legal moves between them, are domain artifacts
— a graph held in `domain/`, exercisable with no model and no adapter in the loop. The
deterministic in-memory capture adapters drive off that graph rather than carrying a mode
machine of their own.

The capture graph has two phases — conversing and note drafting — and both moves between them.
Neither is terminal while the session is open, and the graph has no edge returning to its own
phase. Whatever guard the return edge from note drafting carries, its condition is never
permanently unsatisfiable while the session is open: a phase that cannot be left is terminal,
which FR-02 forbids. That guard's concrete shape is left to contract shaping.

The current phase is state on the `CaptureSession` aggregate. It is the only durable carrier
of the session's mode: every request rehydrates the state machine from it, so no mode
information survives between requests anywhere else.

The state machine is the domain's orchestrator for a capture turn. It holds the invariants —
which moves are legal from the current phase — and answers two questions: which tools are
available in the current phase, and whether a requested move out of it is permitted.

**Tools belong to phases.** A phase declares the tools available while the session is in it,
as a list, and the available set is recomputed on every turn from the session's own state, so
a tool whose work is already done is not offered again. Tools are the model-facing surface:
they propose, read, and compute, and they never change state. Nothing assumes a phase carries
exactly one tool, and nothing in this change routes or selects between them.

**Guards belong to edges.** A guard takes an input and decides whether a move is permitted. The
guard on the move into note drafting requires both that the session holds messages and that a
consent signal is present. The signal originates in an explicit act of the user's; the agent's
part is to recognise it, never to generate it, and no fixed phrase list stands in for it. That
recognition is a model's reading and is therefore fallible; the risk is accepted because the
move back to conversing is always available and because judging model output quality is out of
scope for this effort.

**Actions belong to phases and to edges.** An action is deterministic and domain-side — it is
how something happens in the domain without the model. A phase's actions run while the session
is in that phase, so a turn that crosses no edge still advances the session's state; an edge's
actions run when that move is taken. An action may run in response to a single event applied to
the machine, so state advances during a turn rather than only at its end. Work done within a
phase is expressed as that phase's actions, never as a transition back to itself. An action may
mutate an aggregate in memory and may call a domain port, including an asynchronous one; it
never persists and never commits. The `UnitOfWork` and the commit boundary stay with the
application command, per `context/adrs/hexagonal-arch-shape/decision.md`, which places them in
the application layer and keeps the domain transaction-agnostic.

Those three together satisfy FR-07 structurally rather than by convention: a tool proposes, a
guard permits, an action applies. The model has no path to a state change that does not pass a
guard.

A session's assessed coverage influences the agent's tone and what it says. It gates no
transition, and no guard reads it at any value: coverage expresses how sure of the topic the
user seems, never that the session is finished. Computing it is one of the tools available
while conversing.

The mechanics live in `domain/shared/graph/` and the first concrete composition lives in
`domain/capture/`. Shared holds the mechanics only — guard hooks, tool and action declaration,
and the injection of states and transitions — and knows nothing of capture; it is generic over
the state it carries, and `domain/capture/` binds it to `CaptureSession`. This follows the
effort frame's placement rule (`domain/shared/` holds the abstractions, `domain/capture/` and
`domain/distill/` the concrete children) and the shape `domain/shared/outbox/` already uses in
this repository. The machine is initialised with the aggregate as its state, and an action
receives the session as one of its arguments so that actions can be declared as hooks. The
shared machine is an abstract base class, not a `Protocol`: nothing outside implements it,
capture inherits its mechanics, and `Protocol` in this codebase types ports that other layers
implement. This is the first abstract base class under `backend/src`, and the deviation is
deliberate.

The mechanics are proven by a test suite that exercises a machine other than capture's, so that
reusability is a tested claim rather than an assertion; capture's own machine is tested
separately for its guards and invariants. Adding a phase or an edge changes only a graph
declaration, never the mechanics.

The application command drives the turn. It owns the stream and the iteration; the machine owns
the policy. When a transition is evaluated is an application decision, not a machine one — the
machine only offers the capability. In this change the handler evaluates it at the start of a
turn: the session is rehydrated, a move is considered, the resulting phase determines which
tools are available, and the adapter is called with them. Each event arriving on the stream is
applied to the machine, which decides whether it warrants running actions against the
aggregates held in memory; text chunks pass through to the client in the same pass. When the
stream ends, the command persists what the turn touched.

The machine is never handed a model-facing port and never consumes the stream itself, which is
what keeps FR-04 cheap, keeps the domain free of the dependency `layering.md` forbids, and
keeps the streaming protocol's types out of the domain's vocabulary.

The command's coupling is to the set of aggregates a turn can touch, not to the graph's
inventory: adding a phase, an edge, an action, or a tool changes no command, while adding a new
aggregate does, because a new repository is genuine application knowledge. No separate record of
what changed is passed back — the machine's state carries the aggregates the turn touched,
including one an action created in memory, and the command reads them from there.

Ease of mapping the domain graph onto any particular model framework is a consequence of its
shape, never a criterion for choosing it. Per FR-09, replacing the adapter library must require
no change under `domain/`.

**Out of scope.**

Persisting or committing from inside the machine. Repository writes and the `UnitOfWork`
stay with the application command.

Rendering a phase's declared tools as provider-facing tool definitions — slice S-04 (FR-06,
FR-07). This change declares which tools a phase makes available; S-04 renders them.

A third "shaping the note" phase, in which a note is refined by targeted actions rather than
regenerated. It has no coverage in FR-01 or FR-02 and returns when it has actions of its
own.

Instructions and their context declarations — slice S-03 (FR-05).

Selecting or routing between a phase's available tools, by a model or otherwise.

Reinventing mode heuristics inside the in-memory adapters. If satisfying this change
requires an adapter to grow a mode machine of its own, the policy has been put in the wrong
layer.

## Requirements

- Cites **FR-01** (`context/efforts/llm-adapter/frame.md`) — the move from conversation into
  note drafting rests with the user; no fixed phrase list stands in for that consent.
- Cites **FR-02** — a session can return from note drafting to conversation and draft again;
  neither direction is terminal while the session is open.
- Cites **FR-03** — assessed coverage is load-bearing on what the agent says and when it
  encourages a move, not carried only as telemetry.
- Cites **FR-04** — the phases of the capture flow and the legal moves between them are
  domain artifacts, exercisable by unit tests with no model and no adapter in the loop.
