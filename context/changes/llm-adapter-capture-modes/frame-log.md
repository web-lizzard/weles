## Current State

Session closed. Everything raised is settled into `frame.md` or deliberately parked for
`/discover-contracts`, with the reasoning in the log below.

Carried forward, deliberately undecided: whether edge guards and tool-availability predicates
are one mechanism or two; the names of both phases' tools and actions, keeping the session
topic distinct from the note's `Topic` aggregate; the return edge's concrete guard (constrained
in the body — it may exist, it may never permanently close); and whether the mechanics suite's
non-capture machine is a throwaway fixture or a second real graph.

Two things a later reader should not have to reconstruct. First, the author's longer motive:
Weles is intended to grow toward reading repositories and analysing flashcards, which would
multiply phases and transitions well beyond capture's two — that is why the mechanics sit in
`domain/shared/` rather than in capture. Second, the parked "shaping the note" phase is the
most likely next scope question for this graph.

## Log

### 2026-09-12 — graph-state-machine: Transitions as a domain state machine — OPEN

The author proposes modelling conversation-phase transitions as a graph/state machine in
domain code, with actions as injectable domain functions, later driven by the in-memory
adapter. This is consistent in direction with effort FR-04 ("phases and the legal moves
between them are domain artifacts, exercisable with no model and no adapter in the loop",
`context/efforts/llm-adapter/frame.md`), but the *machine-with-injected-actions* shape is a
solution proposal, not yet a requirement. Raised, not resolved.

**Why:** The framing must separate "phases and legal moves are domain artifacts" (what) from
"a generic state-machine module with injected callables" (how) before either is settled.

### 2026-09-12 — slice-reach: Tools and instructions pulled into S-02 — OPEN

The proposal names tool-calling for topic extraction, a confidence-assessment port, and
instructions inside this change. The roadmap assigns instructions to S-03 (FR-05) and tools
to S-04 (FR-06, FR-07), both listing S-02 as prerequisite
(`context/efforts/llm-adapter/roadmap.md`, `## Dependencies`). S-02's own acceptance is
FR-01, FR-02, FR-03, FR-04.

**Why:** Either the roadmap's decomposition is wrong and should be revised deliberately, or
this change's boundary excludes tools and instructions. Both are live; neither is decided
by silently doing the work.

### 2026-09-12 — graph-state-machine: Phases and legal moves belong in the domain — ACCEPTED

The graph itself — which phases a capture session has and which moves between them are
legal — is settled as domain material, and the in-memory adapters drive off it rather than
holding their own mode machine. Written into `frame.md`'s Boundaries and Requirements
citing FR-04.

**Why:** Directly restates effort FR-04 and the effort frame's out-of-scope clause
("Reinventing conversational mode heuristics inside the deterministic in-memory adapters is
out of scope", `context/efforts/llm-adapter/frame.md`). Grounded, uncontested, and
independent of the still-open questions about the machine's shape. The *shape* of the
artifact (generic machine vs enum-plus-table) stays open under this same idea-id.

### 2026-09-12 — shaping-phase: "Shaping the note" is a new phase, not a ported heuristic — OPEN

The author names three phases carried by today's heuristic: conversing, drafting, shaping.
Only two exist in code. `_should_draft` (`reply_generation.py:74`) splits the drafting path
from the conversational one, and redraft is wholesale regeneration of topic, tags and
content in `send_message.py` `_apply_redraft` — no partial-edit or refinement surface
exists anywhere in capture. `Note` exposes `update_content`, `change_topic`, `add_tag`,
`remove_tag` (`domain/capture/note.py`), but nothing in the reply path drives them
selectively.

**Why:** It changes what this change is. "Move the heuristic into the domain" is a
relocation with a known target; "introduce a third phase" adds behaviour the effort frame
never named — FR-01 and FR-02 speak only of conversing and note drafting. Whether shaping
belongs in S-02, in a later slice, or is really drafting re-entered, is not yet decided.

### 2026-09-12 — phase-location: The phase is CaptureSession state — ACCEPTED

The current phase lives on the `CaptureSession` aggregate, shared across requests; every
request rehydrates the state machine from it. Settled into `frame.md`'s Boundaries.

**Why:** Author's decision, and it is the only placement that makes the phase survive
between requests without a second store. It supersedes the turn-1 alternative of a phase
artifact sitting beside the aggregate.

**Consequence:** `SessionStatus` (OPEN/CLOSED) is no longer the whole of a session's state,
and `draft_note`'s single-draft guard (`domain/capture/capture_session.py:44`) sits under
whatever FR-02 requires of re-entry. How that resolves is `/discover-contracts` work, not
framing.

### 2026-09-12 — machine-role: The machine decides and declares, it does not mutate — ACCEPTED

The machine is the domain's orchestrator for a capture turn: it holds legal-move invariants,
answers whether a requested move is legal, and declares which actions are available on that
move. Guards take an input and check invariants; actions are domain functions declared by
the machine and injected into tool calls by an adapter. The machine performs no aggregate
mutation. Settled into `frame.md`'s Boundaries.

**Why:** Author's decision, with the guard/action split taken from state-machine libraries
in production use (xstate). It resolves the turn-1 "decides vs executes" question as
*decides and declares* — which keeps the aggregate mutation where FR-07 already puts it.

### 2026-09-12 — coverage-role: Coverage shapes tone, gates nothing — ACCEPTED

Assessed coverage influences the agent's tone and what it says; it gates no transition and
cannot substitute for the user's decision. Settled into `frame.md`'s Boundaries.

**Why:** Author's decision, and it is the only reading that satisfies FR-03 and FR-01 at
once — load-bearing on the agent's speech, never on the user's consent.

### 2026-09-12 — slice-minimum: Two edges, not one, is S-02's floor — ACCEPTED

A machine with a single transition was proposed as S-02's tracer bullet, with extensibility
deferred to S-03. Rejected as the slice's content and replaced with: two phases, both edges,
one guard carrying the user's consent, one declared action on the drafting move, coverage
feeding tone, plus a mechanics-level test on a non-capture machine.

**Why:** S-02's acceptance is FR-01–FR-04 (`context/efforts/llm-adapter/roadmap.md`, S-02)
and FR-02 requires both directions with neither terminal; one transition closes the slice
with a criterion unmet. S-03 is instruction-context (FR-05) and has no room in its outcome
for an extensibility proof — deferring there would have been a roadmap change disguised as a
reinterpretation. The added cost over the one-edge version is one edge and one test.

**Consequence:** The extensibility claim is falsified inside S-02 by the same suite that
proves the mechanics reusable — one artifact, not two.

### 2026-09-12 — shaping-phase: Shaping deferred out of S-02 — PARKED

A third phase for refining an existing note by targeted actions is out of this change's
boundary. Not rejected — deferred until it has actions distinct from drafting's.

**Why:** FR-01 and FR-02 name only conversing and note drafting; a third phase would be
behaviour the effort frame never scoped. Supersedes the open question raised 2026-09-12
under this idea-id.

### 2026-09-12 — shared-mechanics: Mechanics in domain/shared/graph, capture composes first — ACCEPTED

The state-machine mechanics — guard hooks, action declaration, injection of states and
transitions — live in `domain/shared/graph/`, with capture's graph as the first concrete
composition. Two test levels: mechanics proven against a non-capture machine, capture's own
machine tested for its guards and invariants.

**Why:** Already settled one level up — the effort frame places abstractions in
`domain/shared/` and concrete children in `domain/capture/` and `domain/distill/`
(`context/efforts/llm-adapter/frame.md`). The repository already runs this exact shape:
`backend/src/domain/shared/outbox/` with `backend/tests/unit/shared/test_outbox_contract.py`
alongside `test_outbox_model.py`. The author's motive — a later distill machine reusing the
mechanics — needs no speculative modelling of distill to be honoured, since shared holds
mechanics only.

**Consequence:** A mechanics suite that exercises only capture's machine would be testing
capture and calling it a contract. The non-capture machine is what makes the reusability
claim falsifiable, and it is the same artifact as the extensibility test.

### 2026-09-12 — action-list: A transition declares a list of actions — ACCEPTED

A transition declares zero or more actions as a list; nothing assumes exactly one. Selecting
or routing between them — by a model or otherwise — is out of scope here.

**Why:** The list shape is the natural one and costs nothing, so it is not a speculative
concept; a router would be. Keeping the shape while refusing the router is what leaves
model-driven action routing possible later without building it now — the same reasoning the
effort frame applies to agent handoff.

### 2026-09-12 — action-remit: An action produces values, never state — ACCEPTED

The question was whether an action may construct a value object given FR-07's ban on
mutating an aggregate. It may. But the boundary is not the type: it is whether the result is
assigned, persisted, or given identity.

**Why:** `Label` and `SessionTopic` are frozen value objects
(`backend/src/domain/capture/value_objects.py:46,100`) and constructing them changes
nothing. `Topic.mint()` and `Tag.mint()` (`domain/capture/topic.py`, `tag.py`) mutate nothing
either, yet must stay outside an action's remit — their results carry `TopicId`/`TagId`, go
through `TopicRepository.add`, and the mint-or-reuse decision belongs to `VocabularyResolver`
via `EmbeddingPort`, needing vocabulary the model cannot see. The sharpest case is
`SessionTopic`: an action may construct it, but `CaptureSession.assign_topic`
(`capture_session.py:41`) mutates the aggregate and stays with the command.

**Consequence:** Actions in this change are named as proposals, not creations. Today's
`DraftTopicChunk` / `DraftTagChunk` already carry only a `Label`
(`application/capture/value_objects.py`), so the existing chunk protocol is already
FR-07-shaped and is the precedent to follow rather than replace.

### 2026-09-12 — consent-signal: The signal is an explicit user act, recognised by the model — ACCEPTED

The guard into note drafting requires messages present and a consent signal present. The
signal originates in an explicit act of the user's; the model recognises it rather than
generating it. That recognition is fallible and the risk is accepted.

**Why:** Author's decision. It is bounded on two sides: the effort frame already puts
evaluation out of scope ("Quality is judged empirically, by using the thing",
`context/efforts/llm-adapter/frame.md`), and FR-02's always-available return edge is the
recovery path when the reading is wrong. The messages-present half is a genuine port of
today's heuristic — `_should_draft` returns False with no user entry
(`reply_generation.py:74`) — as distinct from the phrase list, which is not ported.

### 2026-09-12 — coverage-role: Coverage is certainty, not completion — ACCEPTED

No guard reads coverage at any value, including 1.0. Coverage expresses how sure of the topic
the user seems, not that the session is over. Extends the 2026-09-12 entry under this
idea-id with its reason.

**Why:** The author's point that this *strengthens* the guard is right: with coverage
excluded, the model has no path by which its own assessment could trigger a transition. That
is what makes FR-01's "never performs it unprompted" enforceable rather than aspirational.

### 2026-09-12 — action-list: Actions belong to states, not transitions — ACCEPTED

Supersedes the 2026-09-12 entry under this idea-id, which placed the action list on
transitions. A phase declares the actions available while the session is in it; the set is
recomputed each turn from the session's state, so an action already carried out is filtered
out. Guards stay on edges and decide whether a move is permitted. No self-loops.

**Why:** Placing actions on transitions left no home for work done within a phase — notably
the per-turn coverage assessment — and the alternative was a self-loop the author rejected.
Actions-in-states removes the need for both. It also matches existing code: `if session.topic
is None` (`send_message.py:83`) is already an availability filter over an action, sitting in
the command rather than the domain, which makes relocating it a real port of existing logic
rather than new behaviour.

**Consequence:** `SessionTopic` proposal is an action available while conversing, filtered
out once the session carries a topic; `CaptureSession.assign_topic` stays with the command
per the action-remit boundary. `ConfidenceAssessment` presently lives in
`application/capture/value_objects.py`; as an action result it would belong under `domain/` —
a contracts question, not a framing one.

### 2026-09-12 — action-list: Tools on phases, actions and guards on edges — ACCEPTED

Supersedes both earlier entries under this idea-id. The concept splits in two: **tools** are
the model-facing surface and belong to phases, filtered per turn from session state; they
propose, read and compute and never change state. **Actions** are deterministic, domain-side,
and belong to edges — how something happens in the domain without the model. **Guards** also
belong to edges and decide whether a move is permitted.

**Why:** The single "action" concept was carrying two jobs — what the model may invoke, and
what the domain does on its own — and every earlier difficulty in this session came from that
conflation: where per-turn work hangs with no self-loops, and how FR-07 is enforced. Split
apart, FR-07 holds structurally rather than by convention: a tool proposes, a guard permits,
an edge action applies, and no model-originated state change bypasses a guard.

### 2026-09-12 — action-remit: An action may mutate in memory, never persist — ACCEPTED

Supersedes the 2026-09-12 entry under this idea-id, which held that an action only produces
values. An edge action may mutate an aggregate in memory and may call a domain port,
including an asynchronous one. It never writes through a repository and never commits.

**Why:** `context/adrs/hexagonal-arch-shape/decision.md` makes commands "the exclusive owners
of the commit boundary through an application-defined `UnitOfWork` port — not a domain port",
and explicitly rejects domain-owned transactions (Alternatives, item 1). It does not forbid
domain code from mutating a domain aggregate, which is ordinary domain work. The author
confirmed the `UnitOfWork` stays in the handler, so the line falls between in-memory mutation
(domain) and persistence (application) rather than between mutation and value production.

**Consequence:** The earlier boundary sentence "the machine never performs the aggregate
mutation itself" is withdrawn; what it was protecting — FR-07 — is now carried by the
tool/action split instead.

### 2026-09-12 — slice-reach: S-02 declares tool availability, S-04 renders — ACCEPTED

With tools a first-class concept on phases, this change owns the declaration of which tools a
phase makes available and their per-turn filtering. Slice S-04 owns rendering them as
provider-facing tool definitions and the no-mutation rule (FR-06, FR-07). S-03 keeps
instructions (FR-05). Settled into `frame.md`'s Boundaries and out-of-scope list.

**Why:** Resolves the thread opened 2026-09-12 under this idea-id. The roadmap's decomposition
survives — the seam moves, the slices do not merge — because the declaration is unusable
without the graph that hosts it, while rendering is unusable without a provider.

### 2026-09-12 — framework-neutrality: Mapping ease is a consequence, not a criterion — ACCEPTED

Ease of mapping the domain graph onto a particular model framework may be observed but never
used as an argument for a shape. Settled into `frame.md`'s Boundaries.

**Why:** FR-09 requires that replacing the adapter library change nothing under `domain/`. A
shape chosen because it maps cleanly onto one library carries that library's imprint even
with no import. The author agrees the mapping argument is supporting, not deciding.

### 2026-09-12 — machine-input: Generic mechanics, capture binds the aggregate, ABC not Protocol — ACCEPTED

`domain/shared/graph/` is generic over its state and knows nothing of capture;
`domain/capture/` binds it to `CaptureSession`. The machine is initialised with the aggregate
as state, and actions receive the session as an argument so they can be declared as hooks.
The shared machine is an abstract base class, not a `Protocol`.

**Why:** Resolves the input-seam thread. ABC is the right tool and not an inconsistency:
`Protocol` throughout this codebase types ports implemented by another layer
(`domain/shared/outbox/ports.py`, `domain/capture/ports.py`), whereas capture *inherits* the
mechanics — shared implementation, not structural typing. `grep` finds no `ABC` under
`backend/src`, so this is the first; recorded here so it does not read as a slip later.

### 2026-09-12 — change-record: A turn returns a record of what changed — OPEN

An action mutates aggregates in memory but never persists, so a turn must hand the command an
explicit record of what changed. The concept is accepted; its shape is not. Two candidates: a
dirty set of aggregates to save, or a list of domain facts the command interprets.

**Why:** The dirty-set form puts persistence thinking inside the domain, which
`context/adrs/hexagonal-arch-shape/decision.md` resists ("no notion of transactions, HTTP, or
storage technology"). The facts form has a precedent already running in this repository:
`NoteApprovedPayload` is built in `domain/capture/outbox.py` and appended by the command
(`approve_note.py:35`). Recommended but not decided.

**Consequence:** The record is not the outbox. The outbox carries integration events after
commit; this record tells the command what to persist. One may later feed the other, but
conflating them would give a single artifact two jobs — the same conflation that the
tool/action split had to undo earlier in this session.

### 2026-09-12 — turn-control: The command drives the turn; the machine is never given a model port — ACCEPTED

Of the three candidates — command drives, machine drives, adapter drives — the first is
chosen. The machine answers questions and runs actions; it never holds a model-facing port.

**Why:** The author's objection to command-driven control was that a change in the machine
would then force a change in the command. It does not: every driving step is generic, and the
only command-specific knowledge is which repositories to write — knowledge `layering.md`
forbids the domain to hold anyway. So the command couples to the *set of aggregates* a turn
can touch, not to the graph's inventory; adding a phase, edge, or action changes no command,
while adding an aggregate does, correctly. Machine-driven control would put a model port
inside the domain, against `layering.md` and at the cost of FR-04's cheapness;
adapter-driven control would return policy to the adapter, which the effort frame rules out.

### 2026-09-12 — change-record: No record; the machine's state carries what changed — ACCEPTED

Supersedes the 2026-09-12 OPEN entry under this idea-id. No spec or fact list is returned. The
machine's state holds the aggregates the turn touched, including one an action created in
memory, and the command reads them from there.

**Why:** The author's own observation — with the command driving and holding the machine, what
changed is visible in the state rather than in a description of the state. A record of which
actions ran would additionally have coupled the command to the action inventory, undoing the
extensibility the boundary already promises.

### 2026-09-12 — action-list: Actions attach to phases as well as edges — ACCEPTED

Extends the 2026-09-12 entry under this idea-id. A phase declares actions as well as tools;
an edge declares a guard and actions. A turn spent in a phase runs that phase's actions, so
state advances without a transition.

**Why:** Resolves the first-turn problem that stood open for four turns: the session topic is
assigned on the very first message (`send_message.py:83-86`) while no edge is crossed. Edge-only
actions left that work homeless, and the author had already rejected self-loops. Attaching
actions to phases is symmetric with tools, needs no self-loop, and adds no special case.

### 2026-09-12 — streaming: The machine governs a turn, not a stream — ACCEPTED

Tools are declared before the model call; guards and edge actions are evaluated once the
model's output is complete. Actions do not fire mid-stream.

**Why:** The author raised streaming as a risk to command-driven control. The pattern already
exists: `GenerateReplyCommand.handle` consumes the whole `async for` over `generate(...)`,
yielding SSE events as they arrive, and does its aggregate work in the `if saw_draft:` block
*after* the loop. And because the phase is durable aggregate state rehydrated per request, a
transition decided at the end of a turn simply becomes the phase the next request starts in —
no mid-stream transition is needed. The one genuine mid-stream domain call,
`VocabularyResolver.resolve_topic` on a `DraftTopicChunk`, mints and persists an aggregate and
therefore sits on the command's side of the boundary already; it is not a machine action.

### 2026-09-12 — streaming: The command owns the stream and applies events to the machine — ACCEPTED

Supersedes the 2026-09-12 entry under this idea-id, which held that the machine governs a turn
and no action fires mid-stream. The command owns the iterator and applies each arriving event
to the machine, which decides whether it warrants running actions against in-memory
aggregates; text chunks pass through to the client in the same pass. The machine still never
consumes the stream and never holds a model-facing port.

**Why:** The earlier resolution assumed one homogeneous reply stream. With a general adapter
emitting chunks from several function calls, per-event decisions are required — the shape
already present in `send_message.py`, where `async for chunk` dispatches on chunk type. Moving
that dispatch into the graph is the author's goal and is an improvement. What does not move is
ownership of the iterator: a machine consuming the stream would become an effect runner paced
by the model, and it would need the chunk types — which live in
`application/capture/value_objects.py` — inside `domain/`, against `layering.md`'s zero-import
rule, making the streaming protocol part of the domain vocabulary and putting FR-09 at risk.

### 2026-09-12 — turn-control: The application chooses when the transition is evaluated — ACCEPTED

Extends the 2026-09-12 entry under this idea-id. The machine does not decide when a transition
is considered; it offers the capability and the application picks the moment. In this change
the handler evaluates it at the start of a turn, then pulls the tools for the resulting phase
and calls the adapter.

**Why:** Author's correction. Keeping the timing in the application makes the mechanism
universal — a later flow may evaluate transitions at a different point, or several times, with
no change to the machine. Start-of-turn evaluation also fits the settled model where the phase
is durable aggregate state rehydrated per request: whatever the previous turn applied is
already on the aggregate when the next turn opens.

### 2026-09-12 — return-edge: The return edge may be guarded but never permanently closed — ACCEPTED

The move from note drafting back to conversing may carry a guard; its condition must never be
permanently unsatisfiable while the session is open. The concrete guard is left to contract
shaping.

**Why:** FR-02 makes neither direction terminal. A guard that can lock permanently would make
the drafting phase conditionally terminal and break that requirement, so the constraint is a
framing matter even though the guard itself is not.

### 2026-09-12 — mechanics-suite: The mechanics are proven on a non-capture machine — ACCEPTED

The mechanics suite exercises a machine that is not capture's. Whether that is a throwaway
fixture or a second real graph is left to contract shaping; either satisfies the constraint.

**Why:** A suite exercising only capture's machine would be testing capture and calling it a
contract, leaving the reusability claim — the reason the mechanics sit in `domain/shared/` at
all — unfalsified.

### 2026-09-12 — guard-concept: One guard concept or two — PARKED

Whether edge guards and tool-availability predicates are one mechanism used in two places or
two concepts in the mechanics is deferred to contract shaping.

**Why:** Author's call. It is a question about the mechanics' interface, which is shaped
against real code in `/discover-contracts` rather than argued in prose. Nothing in the frame
depends on the answer.

### 2026-09-12 — naming: Tool and action names deferred — PARKED

Naming the tools and actions of both phases — including keeping the session topic distinct
from the note's `Topic` aggregate — is deferred to contract shaping.

**Why:** Author's call, and names are better settled against the interfaces they sit on. The
constraints that do bind are already in the frame: tools propose and never change state,
actions are deterministic and domain-side, and conversational tone is an instruction belonging
to slice S-03.
