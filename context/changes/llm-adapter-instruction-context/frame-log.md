## Current State

Session closed. No open threads: every question it raised is settled in `frame.md`'s body,
which is now frozen.

Two things a later reader should take from the log rather than rediscover:

- The consent phrase list in the deterministic adapter is settled as an impersonation
  mechanic **together with** the rider that it is not evidence for FR-01. The two halves
  travel together; the rider is what keeps the decision from reading as an exemption, and it
  is what should stop an acceptance scenario being written against six English strings.
- `sessions-as-events` is PARKED, not rejected. The body's constraint that nothing here may
  foreclose it is the live part of that parking.

One cost estimate given during the session was wrong and corrected in the log: keeping a
history of coverage assessments does not need a schema change, because this repository has no
SQL persistence at all.

## Log

### 2026-09-12 — instructions-are-domain-artifacts: instructions move into the domain — ACCEPTED

Carried in from upstream rather than decided here. The effort frame names instructions as
one of the three kinds of domain material (`context/efforts/llm-adapter/frame.md`,
`## Boundaries`), FR-05 pins the context declaration, and S-02's frame closes with
"Instructions and their context declarations — slice S-03 (FR-05)" in its out-of-scope list
(`context/archive/changes/2026-09-12-llm-adapter-capture-modes/frame.md`). Today the prose
is two module-level constants in the pydantic-ai adapter, selected by an `if` on the phase
(`backend/src/adapters/out/llm/capture/agent.py:46-56,120-124`) — exactly the placement the
effort forbids.

**Why:** nothing about this is contested; recording it so the session argues shape, not
whether.

### 2026-09-12 — builder-holds-the-guard: the completeness guard lives in the builder's logic — ACCEPTED

The builder is neither a port nor an adapter: it is a declared domain protocol for
constructing an instruction, and FR-05's guard is part of that construction rather than a
separate check performed beside it. Each phase's builder is unit-tested on its own model.

**Why:** this is the "make the illegal state unrepresentable" reading of FR-05, and it is
stronger than an inspectable required-slot set checked before dispatch — if an incomplete
instruction cannot be constructed, there is no dispatch path to guard. It also matches how
this codebase already enforces graph invariants: `Graph._validate_edges`
(`backend/src/domain/shared/graph/model.py`) refuses a malformed declaration at construction
rather than at use, and `Tool._result_discriminator_matches_name` does the same for tools.

**Consequence:** the claim holds only while the builder is the sole construction path. If the
instruction type stays freely constructible from a finished string, this reverts to a
convention. Carried as thread 1 in `## Current State`.

### 2026-09-12 — instruction-per-phase: one instruction per phase, not per flow — ACCEPTED

Each phase wants the model to behave differently, and different prose per phase is the
mechanism that forces it. The phase therefore authors its own instruction, built from the
turn's context and passed to the adapter.

**Why:** it puts the instruction next to the other two things a phase already decides per
turn — which tools it offers and which actions an event warrants
(`backend/src/domain/shared/graph/model.py`, `State.get_tools` / `State.get_actions`) — so
the phase stays the single place a turn's model-facing policy is decided. The alternative,
one flow-level instruction parameterised by phase, reproduces the `if phase is DRAFTING`
that `agent.py:120` performs today, just moved one layer down.

### 2026-09-12 — coverage-reaches-the-domain: assessed coverage returns to the machine and persists — ACCEPTED

On the real LLM path coverage never reaches the turn today. `_event_from_tool_result`
(`backend/src/adapters/out/llm/capture/agent.py:216`) maps five tool results to events and
`CoverageAssessed` is not among them; `turn.coverage_confidence` is written only by the
in-memory adapter (`backend/src/adapters/out/in_memory/capture/capture_agent.py:102`) and is
read once as telemetry on the reply event (`send_message.py:133`). Coverage will come back as
an event applied to the machine and be persisted.

**Why:** FR-03 requires coverage to be load-bearing on what the agent says. An instruction
built from context cannot interpolate a value the domain never receives, so the first real
slot of instruction context does not exist until this is closed.

**Consequence:** where it persists, and whether it is a running session-level assessment or a
per-turn value that outlives the stream, are open — thread 4 in `## Current State`.

### 2026-09-12 — phase-holds-the-builder: the phase owns its builder and builds per adapter call — ACCEPTED

The instruction is not fetched from somewhere beside the graph. The phase holds its builder
and builds the instruction on each call out to the adapter, from the context the machine
already carries in memory — `CaptureTurn` for capture. The machine exposes it the way it
exposes tools, and the application command passes both across the port together.

**Why:** it makes the instruction the third thing a phase decides per turn, beside
`get_tools` and `get_actions` (`backend/src/domain/shared/graph/model.py`), and it reuses
the path S-02 already built — `StateMachine.get_tools()` asks the current state and hands
the answer on unchanged, and `send_message.py:_open_stream` passes it to
`CaptureAgentPort.converse`. No new ownership, no new lifetime, no second place a turn's
model-facing policy is decided.

**Consequence:** with the phase as the only holder of a builder and the machine as its only
caller, the construction path is single **by composition**. That is weaker than a closed
instruction type, which would make the path single by construction. Thread 1 narrows to:
accept the composed single path, or also close the type. Supersedes the open form of that
thread in the prior `## Current State`.

### 2026-09-12 — instruction-is-blocks: an instruction is an ordered set of named blocks, not an interpolated template — ACCEPTED

Two readings were live: named blocks, some optional, with the required set as the
declaration; or one prose template with named slots, with the slot set as the declaration.
Blocks win, and the session starts cautiously from there.

**Why:** the two differ in where conditionality lives. With slots, coverage is always
interpolated and the model reads the number and decides what to do with it — making coverage
load-bearing on the *model's* reading. With blocks the phase decides whether the model sees
a given piece of prose at all, which puts the decision in the domain where FR-03 wants it and
where a unit test with no model in the loop can hold it. It also matches the rule S-02 already
settled for tools: "a tool the state withholds is never rendered and so can never be called"
(`context/archive/changes/2026-09-12-llm-adapter-capture-modes/frame.md`).

**Consequence:** the guard checks the required-block set at construction. It also splits
authoring from rendering — the domain hands blocks across the port and the adapter turns them
into the provider's instruction payload, the same split S-04 will make for tools. Today
pydantic-ai takes one string (`agent.py`, `instructions=_instructions_for(turn)`); another
library taking a sequence of system messages would need no domain change, which is FR-09.

### 2026-09-12 — building-is-synchronous: building an instruction reaches no port — ACCEPTED

The instruction hook is synchronous and reads only the context the machine already carries.
It takes no `deps` and makes no port call, so vocabulary a block might want to name is not
fetched for it — that is what S-04's tools are for.

**Why (the user's argument):** an instruction answers the model as the turn stands now, not
as it will stand a moment later, and pulling data in to enrich it pays latency for a value
that is stale by the time the model reads it.

**Consequence, grounded:** the cost would be paid more than once per turn. The instruction is
built per call out to the adapter, and `GenerateReplyCommand._dispatch`
(`backend/src/application/capture/commands/send_message.py`) can open two streams in one turn
— conversing, then a transition into drafting, then drafting — so a builder reaching a port
would fetch twice for one user message. It also keeps the hook shaped like its two neighbours:
`State.get_tools` and `State.get_actions` are both synchronous and pure
(`backend/src/domain/shared/graph/model.py`). Widening to an async hook taking `deps` remains
mechanical if a block ever genuinely needs it.

### 2026-09-12 — distill-out-of-scope: the change reaches shared and capture only — ACCEPTED

`domain/shared/` gets the abstraction and `domain/capture/` gets the prose and the concrete
builders. Distill's instructions are not written here.

**Why:** distill has nothing to consume them. `backend/src/domain/distill/ports.py` declares
two repositories and no agent port, its card generation is an in-memory adapter
(`backend/src/adapters/out/in_memory/distill/card_generation.py`), its live adapter is slice
S-06, and it has no phase graph — so a per-phase instruction would need a single-state graph
invented purely to fit the abstraction. That is speculative generality, and the effort frame
already forbids the mirror-image version of it for agents ("an agent concept introduced
speculatively would have to be removed before a real handoff design could land").

**Consequence:** the abstraction is shaped by one flow, and distill is the first test of
whether it generalises. The placement rule naming `domain/distill/` as a home for prose stays
in the body and stays true whenever distill arrives — only the writing of that prose is
deferred.

### 2026-09-12 — coverage-reaches-the-domain: coverage is the latest assessment, overwritten each turn — ACCEPTED

Refines the earlier entry of the same id. The work is scoped into this change: a tool result
comes back as an event, an action applies it, and the value is persisted on `CaptureSession`,
the only durable session-state carrier S-02 left in place. The session holds one value —
the latest — and each turn overwrites it.

**Why:** deferring it leaves the conditional block with nothing to condition on, and the
coverage block is FR-03's motivating case. Overwriting is the cautious start: the blocks the
change actually needs ask "is coverage high", not "is coverage rising".

**Consequence:** a block speaking about a trend is not expressible. Returns if one is ever
wanted.

### 2026-09-12 — sessions-as-events: modelling capture sessions as an event stream — PARKED

Raised by the author while settling coverage persistence: sessions might be better modelled
as events with the aggregate constructed from them. Explicitly at the thinking stage, not
proposed for this change.

**Why parked, not rejected:** it is a reshaping of how session state is stored, not a question
about instructions, and deciding it here would swell a slice whose subject is FR-05. The
effort frame already handles a question of this shape the same way — agent handoff is "neither
adopted nor ruled out", with the constraint that nothing in the effort may foreclose it.

**Consequence:** the same constraint is written into the body for this one. Coverage arrives
through the machine as an applied event rather than being set directly on the aggregate by the
command, so it reaches storage by the route an event-sourced reading would already use. The
in-memory adapter's direct write of `turn.coverage_confidence`
(`backend/src/adapters/out/in_memory/capture/capture_agent.py:102`) is the shape that would
have to go either way.

### 2026-09-12 — coverage-history: overwriting reopened once the persistence cost was checked — OPEN

The author reopened the overwrite decision, wanting the trend kept because "it actually
matters". Checking the cost first: the claim that keeping history means a schema change was
**wrong**, and it was mine. `backend/src/adapters/db/` holds only `__init__.py`, no module
under `src/` imports `sqlalchemy`, and the repository has no `alembic.ini`. Every repository
is in-memory — `InMemoryCaptureSessionRepository` is a `dict`
(`backend/src/adapters/out/in_memory/capture/capture_session_repository.py`) — under the
InMemoryFirst rule (`context/foundation/rules/layering.md`).

**Why this matters:** the case for overwriting rested on history being expensive. It is not.
A series of assessments costs a value object and a collection, and the earlier ACCEPTED entry
for `coverage-reaches-the-domain` chose overwriting against a cost that does not exist.

**Supersedes** the overwrite half of `2026-09-12 — coverage-reaches-the-domain`. The rest of
that entry stands: coverage still arrives through the machine as an applied event.

**Consequence:** two sub-questions now open — whether any block this change ships actually
reads a trend, and where a series would live (a collection on `CaptureSession`, or its own
repository in the shape `MessageRepository` already uses for per-session history).

### 2026-09-12 — coverage-history: the session keeps every assessment, as a collection on the aggregate — ACCEPTED

Resolves the thread opened earlier today. `CaptureSession` holds the assessments as a
collection beside the phase, rather than one value overwritten each turn, and rather than a
repository of its own.

**Why keep a series:** the asymmetry is one-sided. A discarded assessment cannot be recovered
later; a kept one can always be ignored. The cost that argued for overwriting turned out not
to exist. And it is not storage without a reader — a block does read the trend.

**Why on the aggregate:** S-02 settled that the session is "the only durable carrier of the
session's mode", and the phase already lives there
(`backend/src/domain/capture/capture_session.py`). A separate repository in the shape of
`MessageRepository` is the move for reshaping the whole session into events, not for one
field; adopting it now would give session state two storage shapes before that reshaping is
decided. A collection also keeps the value arriving through the machine as an applied event.

### 2026-09-12 — trend-is-a-domain-judgement: the domain computes the trend and sends a word, not a number — ACCEPTED

The direction of coverage is computed deterministically during instruction building and
reaches the model as a word. Rising coverage shifts the agent's tone towards encouraging the
session to close; flat and low affirms keeping it open. The model never reads a coverage
number back.

**Why:** it is the block reading applied to its motivating case. FR-03 asks for coverage to be
load-bearing on what the agent says; computing the judgement in the domain makes that
load-bearing *in the domain*, holdable by a unit test with no model in the loop, instead of
handing the model a float and hoping it reads it as intended. It also stays inside the
already-settled constraint that building is synchronous and port-free — reading a collection
the aggregate already carries costs nothing.

**Consequence:** the number is inbound only. The model supplies an assessment through
`assess_coverage` and never receives one, so no turn depends on the model re-reading a float it
emitted earlier. The float stays available as telemetry on `ReplyDoneEvent`
(`backend/src/application/capture/commands/send_message.py`), which is a different reader with
a different contract. Anyone later "simplifying" this by interpolating the raw number into the
prose would be undoing the decision, not tidying it.

### 2026-09-12 — builder-holds-the-guard: the instruction type is closed to construction from outside — ACCEPTED

Closes the thread the entry of the same id left open. `Instruction` cannot be constructed
except through its builder.

**Why:** the guard argument accepted earlier — an incomplete instruction cannot be built, so
there is nothing to check at dispatch — held only while the builder was the sole construction
path, and that was a property of the composition, not of the type. Closing the type makes it a
property of the type. FR-05 demands "a guard, not a convention", and a freely constructible
value object leaves the invariant resting on nobody choosing to bypass the builder. It is also
cheap under the block reading: a block set is not a value anything else has reason to mint,
unlike `SessionTopic` or `NoteContent`, which callers legitimately construct everywhere.

**Supersedes** the consequence attached to `2026-09-12 — builder-holds-the-guard`, which
recorded the single path as composed and carried the choice forward as an open thread.

### 2026-09-12 — in-memory-renders-instructions: the deterministic adapter speaks from the blocks — ACCEPTED

The roadmap's description of S-03 ends "The in-memory adapters render these instructions
instead of carrying their own text, which is what keeps them thin"
(`context/efforts/llm-adapter/roadmap.md`), and the effort frame says the same. This change
honours it: `DeterministicCaptureAgentAdapter` receives the blocks and speaks from them.

**Why the author's instinct is right, and where it needs splitting.** The constants at
`backend/src/adapters/out/in_memory/capture/capture_agent.py:25-51` are four different kinds
of thing and only one kind is instruction material:

- *Prose the adapter says.* `_HANDOFF_LINE`, `_DEFAULT_SOLID`, `_DEFAULT_SHAKY`,
  `_DEFAULT_TOPIC`, plus the templates inlined in `_conversational_reply` ("You've got a
  handle on: … Let's dig into: …") and `_assess` ("You've articulated: …", "The details
  behind: …"). This is exactly the adapter carrying its own text, and it becomes blocks.
- *Impersonation mechanics.* `_CHUNK_SIZE`, `_CHUNK_DELAY_SECONDS`, `_MAX_TOPIC_WORDS` — how
  a double paces a fake stream and truncates a fake topic. Nothing to do with what an agent
  is told. Stays.
- *Duplicated graph knowledge.* `_NOTE_TOOL_NAMES`, used at line 83 as
  `_NOTE_TOOL_NAMES.issubset(tools_by_name)` to work out that the session is drafting. It does
  not move into the instruction; it is deleted. Once the adapter is handed the current phase's
  instruction, inferring the phase from the tool set is both redundant and the "mode machine
  of its own" the effort frame forbids.
- *A fixed phrase list for consent.* `_CONFIRMATION_PHRASES` — see the entry below.

### 2026-09-12 — consent-phrase-list: a fixed phrase list stands in for consent in the double — OPEN

`_CONFIRMATION_PHRASES` (`capture_agent.py:34-43`) is matched at line 77 and, when it hits,
the adapter yields `DraftingConsentSignalled` — the session moves toward drafting because the
user typed one of six English strings.

FR-01 is explicit: the move into note drafting rests with the user and "no fixed phrase list
stands in for the user's consent". S-02's frame repeats it and adds that recognising consent
"is a model's reading and is therefore fallible". So the shape FR-01 names is in the tree
today, in the adapter FR-01's own acceptance is exercised against.

**Why this is open rather than decided:** there is a real reading in which FR-01 governs the
product's agent and not a test double, whose whole job is to stand in for a model's judgement
by some cheap means. Under that reading the list is legitimate *as impersonation mechanics*.
What follows either way is that it does not become a block: it is either a double's private
trick, which the instruction never carries, or it is a violation to remove. It must not be
given a home in the domain, which would make it policy.

**Consequence:** the decision changes what the in-memory adapter does with the consent block,
and possibly whether one exists at all.

### 2026-09-12 — consent-phrase-list: the list is an impersonation mechanic and stays in the adapter — ACCEPTED

No deterministic adapter can be ready for arbitrary user prose, so the double recognises
consent by a fixed list of phrases. The list stays where it is, does not become an instruction
block, and is not domain policy.

**Why:** FR-01 governs the product's agent, which reads consent with a model and is fallible
in the way S-02's frame already accepted. A double has to stand in for that judgement by some
cheap means, and there is no cheaper one. Giving the list a domain home would have converted
a test double's shortcut into policy, which is the outcome FR-01 was written to prevent.

**Consequence, and the reason this is written into the body rather than only logged:** the
deterministic path's consent recognition is not evidence that FR-01 holds. Anything reading
this frame cold — `/discover-contracts`, `/bdd` — could otherwise write an acceptance
scenario against the phrase list and call FR-01 covered. FR-01 is demonstrated on the
provider-backed path under FR-08, by the author's own manual use. The phrase list exists so
the deterministic path can reach note drafting at all, which ordinary CI needs under
`context/foundation/rules/contract-testing.md`.
