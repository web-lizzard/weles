## Current State

Session closed. The domain is modelled; everything left is `/plan`'s.

**What is on disk.** `backend/src/domain/shared/graph/` holds the reusable mechanics:
`model.py` (`Condition`, `Action`, `ToolArguments`, `ToolHandler` aliases; `ToolResult`,
`Tool`, `State`, `Transition`, `Graph`) and `machine.py` (the
`StateMachine[ContextT, EventT, NameT]` ABC). `backend/src/domain/capture/` holds the first
composition: `turn.py` (`CaptureTurn`, the `CaptureEvent` discriminated union) and `graph.py`
(`CaptureMachine`, `Conversing`, `Drafting`, five tools with their results, the
`consent_given` guard, `_CAPTURE_GRAPH`). `value_objects.py` gained `CapturePhase`,
`capture_session.py` gained `phase` (defaulting to `CONVERSING`) and `enter_phase`, and
`ports.py` gained `CaptureAgentPort` and `MessageRepository.history`.

**The shape, in one pass.** Three type parameters — the aggregate-carrying context, the
event type, and a `StrEnum` naming the states — bound once by a composition. `Graph` is
keyed rather than listed, so duplicate state names and duplicate edges are unconstructible
and only two invariants need a validator. `State` is an ABC that declares full tool and
action inventories and narrows them per turn. `Transition` stays data: a guard plus actions,
named by the keys it is filed under. `Tool` is declaration plus handler and carries no
policy. A move is one edge, never a path. A composition supplies a graph and two aggregate
hooks; everything else is inherited mechanics.

**Verified, not assumed, at close:** `ruff` clean, `basedpyright` 0 errors over all of
`src/`, the graph and `adapters.compose` both import, 498 tests passing. No method bodies
anywhere except `Graph`'s invariant validator and the composition's own declarations.

**Carried to `/plan`.** Whether `Tool.name` and its result's pinned `tool` literal should be
checked by a validator, and how — parked deliberately. That an opaque `ToolArguments` leaves
S-04 with no input schema to render, so either `description` carries it in prose or S-04
adds an input model symmetric to `result`. The naming collision between `State` the graph
node and the aggregate the machine carries, unresolved and harmless. And the fact that
`CaptureAgentPort` makes `application/capture/value_objects.py`'s `ReplyChunk` union
redundant at that seam, together with the collapse of `TopicExtractionPort` and
`ConfidenceAssessmentPort` into tools — a real reach into existing code that this session
declared but did not perform.

**Owed by `/implement`, and the tree is knowingly left red on it.**
`InMemoryMessageRepository` (`adapters/out/in_memory/capture/message_repository.py`) has no
`history` and no longer satisfies its port. The contract test
`tests/unit/capture/contracts/test_message_repository_contract.py:14` annotates the adapter
as the port and so does catch it — the closing commit's basedpyright hook failed on exactly
that line and was overridden with `--no-verify` at the author's explicit instruction, to
keep the session's work from being lost. Writing the adapter method is an implementation and
outside contract shaping. Note that `basedpyright src/` alone stays at 0 errors, because the
only annotation that binds adapter to port lives under `tests/`; an earlier entry in this log
claimed nothing type-checks it, which was wrong and is corrected here. Capture's suite must assert `graph.terminal_states` is empty, and
separately pin that the return edge stays available — it is currently unguarded, which
satisfies that trivially.

**One thing a later reader should not have to rediscover.** This working tree is shared.
Mid-session another process reverted `CapturePhase` and `CaptureSession.phase` out of the
tree and left a broken orphan `NoteVocabulary` behind; a symbol being absent here is not
proof it was never written.

## Log

### 2026-09-12 — guard-concept: Two predicate shapes, not one — ACCEPTED

Resolves the question parked in `frame-log.md` (2026-09-12, `guard-concept`). Tool
availability and edge guards are two aliases, not one: `Availability[ContextT]` reads
the context only, `Condition[ContextT, EventT]` reads context and event. Action
triggers reuse `Condition`.

**Why:** The arity differs for a structural reason, not a stylistic one. Tools are
pulled before the model is called — `get_tools()` has no event to hand a predicate —
while a guard is evaluated against the event that requests the move. Forcing one
signature would mean passing a null event to every tool predicate, which is the
conflation rather than the unification.

**Consequence:** Guards and action triggers do share one alias, so the mechanics carry
two concepts, not three.

### 2026-09-12 — event-type: The machine is generic over its event type — ACCEPTED

`StateMachine[ContextT, EventT]` takes a second parameter. Capture binds it to a
domain-side event type of its own; the command translates arriving chunks into it.

**Why:** `frame.md` has the command applying each arriving event to the machine, and the
chunk types it is iterating live in `application/capture/value_objects.py`. Typing
`apply` against those would put the streaming protocol inside `domain/`, against
`layering.md`'s zero-import rule and the FR-09 risk `frame.md` names explicitly. A type
parameter is the only shape that lets the machine take events without knowing the
transport's vocabulary.

### 2026-09-12 — self-loop: Rejected at construction, not by convention — ACCEPTED

`Transition` raises `SelfTransitionError` from a model validator when `source ==
target`.

**Why:** `frame.md` states the graph has no edge returning to its own phase, and the
actions-on-phases decision exists precisely so a self-loop is never needed. A rule the
mechanics enforce cannot be forgotten by a later composition; a rule in prose can.

### 2026-09-12 — graph-exceptions: The graph declares no exceptions of its own — ACCEPTED

`domain/shared/graph/exceptions.py` and its five `CoreException` subclasses are deleted.
A refused move is a return value; a malformed graph is a `ValueError` from a validator or
a failing mechanics test.

**Why:** The author's point — the machine holds the transitions, so refusing one is
knowledge, not an accident — is reinforced by a repository rule. Every `CoreException`
subclass must earn a row in `EXCEPTION_STATUS_MAP` (`adapters/http/errors.py:6`), enforced
recursively over `__subclasses__()` by `tests/unit/test_http_error_mapping.py:85` per
`context/foundation/rules/exceptions.md`. Five graph exceptions would mean five HTTP status
rows for conditions that can never reach HTTP — three of them (duplicate state, duplicate
edge, unknown state) being developer errors in a static declaration, not domain events.

**Consequence:** `transition` returns `bool` rather than raising, and `current_state` no
longer promises to raise on an undeclared name. Graph well-formedness moves from runtime
to the mechanics suite, which `frame.md` already requires for other reasons.

### 2026-09-12 — tool-shape: A tool declares name, description and a discriminated result — ACCEPTED

`Tool` carries `name`, `description`, `result: type[ResultT]` and `is_available`.
`ToolResult` is a shared base whose children pin `tool` to a `Literal`, making a state's
results a discriminated union. `Tool` is generic in its result type so a composition
narrows it without touching the mechanics.

**Why:** Author's decision. The discriminator is what lets a returning result be traced to
the tool that produced it, and the shape has a precedent already running here —
`ReplyChunkKind` plus `Literal` plus `Field(discriminator="kind")` in
`application/capture/value_objects.py`. Declaring the result type rather than rendering it
keeps the slice boundary `frame.md` draws at S-04.

**Consequence:** The name/discriminator agreement is an invariant with nothing enforcing it
yet, and every concrete `ToolResult` must repeat `frozen=True` or pydantic refuses the
subclass.

### 2026-09-12 — state-name-type: States are named by an enum, not a string — ACCEPTED

A third type parameter, `NameT: StrEnum`, replaces `str` on `State.name`,
`Transition.source`/`target`, `transition`/`can_transition`'s target, and both abstract
aggregate hooks.

**Why:** Author's call on the question left open last turn. `str` let a typo pass as a
target and gave `state_name_of` an untyped return, so the composition's own phase enum was
knowledge the mechanics threw away. Binding it costs one parameter, paid once per
composition, and was checked end to end against a throwaway two-phase graph.

**Consequence:** Three type parameters on `State`, `Transition` and `StateMachine`. That is
the ceiling — anything further belongs to a composition, not the mechanics.

### 2026-09-12 — tool-shape: Availability leaves the tool; the handler takes the context — ACCEPTED

Extends the 2026-09-12 entry under this idea-id. `Tool` loses `is_available` and gains
`handler: ToolHandler[ContextT, ResultT]`, a callable receiving the context. Availability
moves onto the state, which pairs each tool with an `Availability` exactly as it pairs each
action with a `Condition`.

**Why:** Author's decision, and the placement follows from what filtering is for: the
machine decides what is offered, and a tool that is not offered is never rendered, so it
can never be called. A predicate on the tool would have described a condition the tool
itself could not enforce. Pairing it on the state also makes tools and actions symmetric,
which they were not before.

**Consequence:** `Tool` is now purely what S-04 renders plus what runs — no policy on it at
all. Whether the handler's single context argument is enough, or whether a tool needs
model-supplied arguments, is open.

### 2026-09-12 — instruction-location: Instructions are domain material — ACCEPTED

`description` on a tool stays in the domain, and instructions will be domain material too
when S-03 reaches them.

**Why:** Author's decision, recorded here because S-03 will otherwise have to re-argue it.
The text a tool shows the model is inseparable from the tool's declaration; only the
rendering of it is provider-facing, and `frame.md` already assigns rendering to S-04.

### 2026-09-12 — tool-availability: A state decides its own eligibility, as a method — ACCEPTED

Supersedes the pairing accepted earlier today under `tool-shape`. `State` becomes an
abstract base class. Tools and actions are declared as full inventories on abstract
properties, and eligibility is decided by `get_tools(context)` and
`get_actions(context, event)`, both defaulting to the whole inventory and overridden by a
state that filters. The `Availability` alias is deleted; `Condition` survives on
`Transition.guard` only.

**Why:** Author's proposal, and it fixes a real limit in the form it replaces. Independent
per-tool predicates can only ask about one tool at a time, so "offer B only while A has not
yet done its work" was inexpressible — and that is precisely the shape of the author's own
case, a session sitting in one phase for many turns while its tool set narrows. Eligibility
is a statement about the phase, not about a tool in isolation. A named method is also
testable and readable in a way a lambda in a pydantic field is not.

**Consequence:** The unfiltered inventories are kept deliberately, beyond what was proposed,
so a phase's full capability stays inspectable without a context — otherwise nothing could
enumerate what a phase can ever do, which S-04's rendering and the mechanics suite both
want. It also leaves `State` an ABC while `Transition` is still data, which is an asymmetry
that probably does not survive.

### 2026-09-12 — tool-arguments: The model's arguments are an opaque bag — ACCEPTED

`ToolHandler` becomes `Callable[[ContextT, ToolArguments], Awaitable[ResultT]]`, where
`ToolArguments` is `Mapping[str, object]`. The mechanics carry what the model sent and
never model it; a handler needing structure parses it into a shape of its own.

**Why:** Author's call, having no preference between a declared input model and a bag. The
bag keeps the mechanics out of the business of describing model input, which is consistent
with `frame.md` sending rendering to S-04.

**Consequence:** The cost is real and named here so S-04 does not rediscover it. `result` is
a declared type and can be rendered as a schema; arguments are not, so nothing in this
slice tells a provider what a tool expects to receive. Either `description` carries that in
prose, or S-04 adds a declared input model symmetric to `result`. Recorded as a known gap,
not an oversight.

### 2026-09-12 — graph-artifact: The graph is one declared artifact, never derived from context — ACCEPTED

`Graph[ContextT, EventT, NameT]` bundles states and transitions with `state()` and
`outgoing()` lookups. `StateMachine` declares it through one abstract property, replacing
the separate `states()` and `transitions()` methods.

**Why:** The author asked whether the machine should take the graph as a parameter. Bundling
it answers what that was reaching for — one artifact to declare, test and hand around — while
declaring it through an abstract property keeps `frame.md`'s settled decision that capture
*inherits* the mechanics rather than configuring a concrete class. Because `Graph`
constructs standalone, the mechanics suite can build graphs without subclassing a machine,
which is the part a constructor parameter would have bought.

**Consequence:** A composition now supplies exactly two things: the graph, and the two
aggregate hooks. Everything else in `StateMachine` is mechanics.

### 2026-09-12 — graph-artifact: The graph is static, and it is not a tree — ACCEPTED

Building the graph from the context is rejected, and the "tree" reading is corrected to a
cyclic directed graph.

**Why:** Two separate reasons. A graph derived from the context makes "legal from here" a
statement about the context rather than the phase, so no test could pin the legal moves
down and `frame.md`'s promise that adding a phase changes only a declaration would not
hold. And capture's graph cannot be a tree at all: FR-02 requires conversing and note
drafting to reach each other in both directions, which is a 2-cycle — no root, no tree
form. Adjacency is the right shape, which is what `Graph` holds.

### 2026-09-12 — graph-artifact: The graph is keyed, and the keys are the names — ACCEPTED

Supersedes the sequence form accepted earlier today under this idea-id. `Graph` holds
`states: Mapping[NameT, State]` and `transitions: Mapping[NameT, Mapping[NameT,
Transition]]`. `State.name` and `Transition.source`/`target` are deleted — each is named by
the key it is filed under.

**Why:** The author asked whether a mapping would serve better than two sequences. It does,
and for a stronger reason than lookup cost: it makes two declaration invariants structural.
A mapping cannot hold two states under one name, and a nested mapping cannot hold two edges
for one source/target pair, so neither is a rule anything has to enforce or test — which is
what the previous turn had written off to the mechanics suite. Removing the duplicated name
fields removes the second failure mode as well, since a key and a field can disagree and a
key alone cannot.

**Consequence:** `State` and `Transition` lose their `NameT` parameter; only `Graph` and
`StateMachine` carry three. What remains to check is two things, written out in `Graph`'s
validator and verified against a throwaway graph: every endpoint names a declared state,
and no edge returns to its own state.

**Supersedes:** the claim that graph well-formedness is caught by the mechanics suite rather
than at construction. Two of the four cases are now unconstructible and the other two raise.

### 2026-09-12 — graph-invariants: The validator stays, because a bad graph cannot reach a request — ACCEPTED

`Graph`'s two `ValueError` checks stay as written. They are not a runtime-error surface: a
malformed graph fails where it is declared, not where it is used.

**Why:** The author's reasoning, and it holds under this repository's wiring.
`adapters/compose.py` builds the whole object graph at module scope (`compose.py:109`
onward) and is imported by `main.py` and every HTTP adapter, so a `Graph` declared at module
level in `domain/capture/` is constructed at import — the process fails to boot rather than
serving a 500. That is also why these `ValueError`s do not undo the earlier decision to give
the graph no `CoreException` of its own: they never travel to a client, so they never need a
`code -> status` row.

**Consequence:** One condition, worth naming so it is not lost. This holds only while the
graph is built at module scope. A graph constructed inside a request handler would turn
both checks into 500s, and the argument for keeping them as plain `ValueError`s would go
with it.

### 2026-09-12 — transition-shape: Transition stays data; the asymmetry with State is right — ACCEPTED

Raised by the model across three turns and resolved here without a change. `State` is an
ABC and `Transition` is a frozen model, and that difference is justified rather than
tolerated.

**Why:** The case for making `Transition` an ABC rested on a strawman of the alternative — a
lambda in a field. A guard can just as well be a named module-level function assigned to
`guard`, which is as readable and as testable as a method, with no class existing only to
hold one. The real difference is that `State` has something to decide per turn: its
inventory narrows as the context advances, which is what `get_tools` exists for. An edge
decides one thing once, from a context and an event, and has no inventory to narrow.
Subclassing it would add a level of indirection that buys nothing.

**Consequence:** Capture's consent guard should be written as a named function, not a
lambda. That is the whole of what the ABC proposal was actually reaching for.

### 2026-09-12 — multi-hop: A move is one edge; several moves is a question, not an act — ACCEPTED

`transition(target)` crosses exactly one edge. A target the current state does not reach
directly is refused even when the graph could reach it in two moves. `Graph` gains
`reachable_from(source)` so the multi-move question can still be asked of the graph.

**Why:** The author asked whether a move could go several transitions further. It must not.
A phase's actions run per turn, through `apply` — so passing through an intermediate phase
inside one move would enter and leave it without any of its work happening, which makes
"the session was in note drafting" mean nothing. It would also contradict the settled turn
model in `frame.md`, where the handler considers one move at the start of a turn and the
phase is durable aggregate state rehydrated per request.

**Consequence:** Reachability is still a real question — it is how one checks no phase is
stranded — so it is answered as a query on the graph rather than smuggled into a move.

### 2026-09-12 — terminal-states: The mechanics report terminal states; a composition forbids them — ACCEPTED

`Graph.terminal_states` returns the declared states with no outgoing edge. It is a query,
not a validator rule.

**Why:** This closes a gap the author's question exposed. `frame.md` requires that neither
capture phase is terminal while the session is open — and nothing in the mechanics encoded
it, so FR-02's most load-bearing structural claim was a sentence with no test behind it.
But it is capture's requirement, not the mechanics': a generic graph may legitimately have
a terminal state, so forbidding it in `domain/shared/` would push one flow's policy into
code meant to serve distill and later flows too. Reporting it lets capture's own suite
assert the emptiness.

**Consequence:** An obligation on the capture composition, recorded above so it is not lost
between turns: assert `terminal_states` is empty in capture's suite.

### 2026-09-12 — terminal-states: Structural terminality is the only half a graph can see — ACCEPTED

Extends today's entry under this idea-id. `terminal_states` reports states with no outgoing
edge and nothing more. A state whose only outgoing edge carries a guard that can never pass
is equally inescapable and is not reported.

**Why:** The author asked whether terminal states are simply those without further
transitions. They are — and that is exactly the limit worth recording, because `frame.md`
constrains both halves: the graph has no edge returning to its own phase, *and* the return
edge's guard is never permanently unsatisfiable. No static reading of a graph can tell an
unsatisfiable guard from one not yet satisfied, so the second half cannot become a property
of the mechanics at all. Only a test against the specific guard can hold it.

**Consequence:** A second obligation on capture's suite, alongside the emptiness assertion:
pin that the return edge's guard is satisfiable.

### 2026-09-12 — edge-availability: Two senses of "available", kept apart on the graph — ACCEPTED

`Graph.outgoing(source)` returns every edge leaving a state, by target, guards unevaluated
and empty rather than absent for a state with none. `can_transition` keeps answering both
senses at once.

**Why:** The author's question — whether a transition is available for a state — has two
answers that look alike and behave differently. Structural absence is permanent: the graph
has no such edge and never will while the declaration stands. A failing guard is about this
turn only. Collapsing them into one bool is right for a caller about to move, and wrong for
one reasoning about the session — and FR-02's whole constraint lives in the second sense,
not the first.

**Consequence:** `terminal_states` is definable in terms of `outgoing`, and a caller that
wants to say "this move exists but is not permitted yet" has a way to know it.

### 2026-09-12 — terminal-states: `is_terminal` alongside the set, and the read surface closes — ACCEPTED

`Graph.is_terminal(name)` is added. `terminal_states` is redefined as every state that
`is_terminal`.

**Why:** Author's suggestion. The two forms are not redundant, they have different users: a
suite asserts against the set, because a phase added later is then caught without anyone
remembering to extend the assertion, while a caller holding one state asks the singular.
Naming the set in terms of the bool also makes the structural-only caveat live in one place
rather than two.

**Consequence:** `outgoing`, `is_terminal`, `terminal_states`, `reachable_from` — the
graph's read surface is treated as closed from here. Another query goes in when something
calls it, not before; the mechanics already carry more than this slice's two phases
exercise, and the line has to sit somewhere.

### 2026-09-12 — turn-context: The machine's context is a turn, not the session alone — ACCEPTED

`ContextT` binds to `CaptureTurn`, holding `session`, `note` and `message_count` — not to
`CaptureSession`.

**Why:** Forced by two things `frame.md` already settled, which a bare aggregate cannot
satisfy together. The command reads what a turn touched off the machine's state "including
one an action created in memory" — and `CaptureSession` holds only a `NoteId`, so a note
drafted this turn has nowhere to live. And the guard into drafting requires that the session
already holds messages, which no capture aggregate knows: messages are their own repository
and the count reaches the domain as a fact the command passes in from the transcript it
already reads. The frame's phrase "initialised with the aggregate as its state" is honoured
in substance — the session is still the only durable carrier of the phase, which is what
that sentence was protecting — but not literally.

**Consequence:** `state_name_of` and `enter_state` reach through `context.session`. The
turn is per-request and never persisted; it is a carrier, not an aggregate.

### 2026-09-12 — naming: Capture's tools, events and phases named — ACCEPTED

Resolves the naming parked in `frame-log.md`. Phases are `CapturePhase.CONVERSING` /
`DRAFTING`. Conversing offers `assess_coverage` and `propose_session_topic`; drafting offers
`propose_note_topic`, `propose_note_tag`, `propose_note_content`. Events are `TurnOpened`,
`ReplyProduced`, `SessionTopicProposed`, `NoteTopicProposed`, `NoteTagProposed`,
`NoteContentProduced`.

**Why:** The frame's one binding constraint was keeping the session's topic distinct from the
note's `Topic` aggregate, and the `session` / `note` prefixes carry that everywhere it
matters — `SessionTopicProposal` returns a `SessionTopic`, `NoteTopicProposal` returns only
a `Label`, because minting a `Topic` needs vocabulary the model cannot see and stays with
the command.

### 2026-09-12 — return-edge: The return edge carries no guard — ACCEPTED

`DRAFTING -> CONVERSING` is declared with `guard=None`.

**Why:** `frame.md` left the concrete guard to contract shaping under one constraint: its
condition must never be permanently unsatisfiable while the session is open, because a
phase that cannot be left is terminal and FR-02 forbids it. No guard is the only shape that
satisfies that by construction rather than by argument, and nothing in the frame names a
condition the return should actually test. A guard goes on when something needs one.

### 2026-09-12 — turn-context: The turn carries the messages themselves — ACCEPTED

Supersedes the `message_count: int` field accepted earlier today under this idea-id.
`CaptureTurn.messages` is a `Sequence[Message]`, and `MessageRepository` gains
`history(session_id) -> list[Message]`.

**Why:** Author's correction, and a count was the wrong reduction. Tools read and compute,
and what they read is the conversation: judging how far the topic is covered is a reading of
what was actually said, which no number can support. The guard's presence check is then just
one use of the same field rather than a reason for a separate one.

**Consequence:** Two that matter, and see Current State for a correction to the second.
The command-side path to messages becomes a domain repository read rather than
`TranscriptQueryPort`, which is what `cqrs-lite.md` prescribes
anyway — queries read DTOs, commands go through domain repositories — so the query port
`send_message.py:87` currently uses inside a command stops being the command's source.
And the in-memory adapter no longer satisfies the port, silently: see Current State.

### 2026-09-12 — phase-default: The phase defaults to conversing — ACCEPTED

`CaptureSession.phase` defaults to `CapturePhase.CONVERSING` rather than being required.

**Why:** Not the convenience argument. `status` has no default because there is no natural
unset status; a phase has one, and it is the start. Every session persisted before this
field exists carries no phase and must rehydrate as conversing, because that is where it
actually was — so the default states something true about rehydration rather than papering
over a missing value. That it also leaves the four existing direct constructions
(`tests/unit/capture/test_model.py:154,165`,
`tests/unit/capture/test_send_message_command.py:88,194`) untouched is a consequence, not
the reason.

**Consequence:** With the suite running again, the tree is green apart from one
environmental failure that predates this change.

### 2026-09-12 — tool-discriminator: Validating name against the discriminator goes to planning — PARKED

Whether `Tool.name` and its result's pinned `tool` literal should be checked, and by what,
is deferred to `/plan` as an open question.

**Why:** Author's call. The invariant is stated in `ToolResult`'s docstring and nothing in
this slice depends on the enforcement mechanism, so shaping it further here would settle a
question nothing is yet pressing.

### 2026-09-12 — agent-port: The model-facing port is a domain port — ACCEPTED

`CaptureAgentPort` is sketched in `domain/capture/ports.py`:
`converse(turn, tools) -> AsyncIterator[CaptureEvent]`. One port for the whole turn, held by
the application command.

**Why:** Author's decision that this belongs in the domain, and it survives `layering.md`
because of what it does and does not carry. `layering.md` permits "any other domain-service
ports, expressed in the domain's own vocabulary, with no notion of transactions, HTTP, or
storage technology" — and every type on this signature is capture's own: `CaptureTurn`, the
graph's `Tool`, `CaptureEvent`. `AsyncIterator` is the only borrowed concept and it is
stdlib. That is also exactly what FR-09 asks: swapping the adapter library changes nothing
on this signature.

It does not contradict `frame.md`'s rule that the machine is handed no model-facing port and
consumes no stream. The rule is about who holds the port, not where it is declared, and the
command still holds it.

**Consequence:** Two that matter. The three existing application ports collapse: topic
extraction and confidence assessment are now tools on the conversing phase, not ports of
their own, and reply generation becomes this. And the domain now *defines* the turn's event
vocabulary rather than the application doing so, which makes
`application/capture/value_objects.py`'s `ReplyChunk` union redundant at this seam — the
command translates nothing, because there is nothing left to translate from.

### 2026-09-12 — agent-port: The adapter invokes tool handlers — ACCEPTED

The tools handed to `converse` arrive filtered by the phase, and the adapter calls their
handlers with the same `turn` it was given.

**Why:** It is the only single-pass shape. The alternative — yielding a "tool called" event
and having the command run the handler and feed the result back — needs a bidirectional
stream, which is a great deal of machinery for a seam that gains nothing by it. Handing the
adapter domain code is not a layering problem: adapters depend on the domain by design, and
a tool reads and computes and never mutates, so nothing about state escapes.

**Consequence:** The adapter holds the turn for the duration of the call. Instructions are
not on this signature and S-03 will have to add them, which is the seam where this port is
expected to grow.

### 2026-09-12 — event-shape: The union is the envelope — ACCEPTED

`CaptureEvent` stays a flat discriminated union, now annotated
`Field(discriminator="kind")` to match the shape already used by `ReplyChunk`. No envelope
with a payload.

**Why:** The author asked whether differing payloads force an envelope. They do not, and
this repository already holds both answers, split by where the message goes.
`OutboxEnvelope` carries `payload: dict[str, object]` because it crosses a process boundary
and the payload has to survive serialization opaquely. `CaptureEvent` never leaves the
process — adapter to command to machine, all within one turn — so the union keeps full types
the whole way, and a guard or action narrows with `isinstance` and already knows the fields.
An envelope would force a downcast at every reader and lose exhaustiveness, paying a
serialization price for a hop that has no serialization.

**Consequence:** If these events ever need common metadata — a sequence number, a timestamp —
an envelope can wrap the union later without the union changing. Nothing needs that now.

### 2026-09-12 — event-shape: Tool results and events stay separate vocabularies — ACCEPTED

A collapse of `CaptureEvent` to `ToolResult | ReplyProduced | TurnOpened` was proposed by
the model on the grounds that `NoteTopicProposal` and `NoteTopicProposed` carry the same
`Label`. Rejected by the author.

**Why:** The two have different audiences and the overlap is incidental, not structural: a
tool result goes back into the model's own context, while an event goes to the machine to
advance domain state. The author's framing is the general form of it — a hexagonal port
takes and returns the domain's own symbols, which is what makes the domain the owner of the
port rather than its client. Collapsing them would have tied the domain's event vocabulary
to whatever the tool surface happens to look like, and the tool surface is S-04's to change.

**Consequence:** The near-duplicate pairs stand deliberately. Recorded so a later reader does
not mistake them for an oversight and merge them.

### 2026-09-12 — tree-drift: Session symbols reverted by another process, restored — ACCEPTED

`CapturePhase` (`value_objects.py`) and `CaptureSession.phase` / `enter_phase` were reverted
out of the working tree by a process outside this session, and a duplicate `NoteVocabulary`
appeared in `value_objects.py` carrying `"Topic"` / `"Tag"` forward references the module
does not import. The first two were rewritten; the duplicate was deleted.

**Why:** The duplicate was verified orphaned before removal, not assumed: every consumer —
`adapters/out/in_memory/capture/note_vocabulary_repository.py:7`,
`domain/capture/ports.py:7` — imports the working class from
`domain/capture/note_vocabulary.py:7`, and nothing referenced the copy. It was also the only
thing holding basedpyright at 2 errors.

**Consequence:** Restored state verified rather than assumed — `ruff` clean, basedpyright
0/0 over `src/`, the graph and `adapters.compose` both import, 498 tests passing. The
closing commit must be staged file by file, since the tree carries work from outside this
session.
