## Current State

Session closed. The contract is on disk and 425 unit tests pass.

**This session overrides `frame.md` on one point.** The frame's sentence that at low coverage
"the model never sees that as an option at all" does not hold and is superseded by
`coverage-shapes-tone-not-capability` and `blocks-shape-tone-tools-shape-capability` below.
The frame stays frozen and is not reopened; where the two disagree, this log is the later
authority. The narrowed reading is: **coverage shapes tone, never capability.** A reader
building scenarios must not assert that the model cannot signal drafting consent at low
coverage — no implementation can make that true without breaking FR-03.

What the contract now says, for a reader who reads nothing else:

- **Three channels reach the model** — tool schemas, message history, and the instruction. The
  instruction is the remainder once the other two are subtracted, so neither tools nor the
  transcript are ever blocks.
- **A block never names a tool**, because prose cannot gate a capability the provider has
  already shown. It may state ordering, which no single `Tool.description` can own.
- **An instruction is an ordered tuple of blocks plus a declared required set**, validated at
  construction. `blocks` is exactly what the model is told; there is no later filter, and no
  path produces an incomplete instruction.
- **Requiredness is static.** A required set computed from the turn would pass by construction
  and mean nothing.
- **The general part is required of capture, not of each phase.** `build` and `required` are
  `@final` on `CaptureInstructionBuilder`; a phase supplies `phase_blocks` and `phase_required`
  and cannot subtract the floor or advertise a set it does not build to.
- **Prose lives in constants.** Literal blocks and templates alike; a builder selects and
  supplies values, never writes prose. `InstructionBlock.rendered` interpolates behind a guard
  that refuses any template/values mismatch, and keeps only the rendered text.
- **Coverage falls as well as rises.** `CoverageTrend` is three-valued with `FLAT` as a band;
  `CoverageReading` is four words — `EARLY`, `DEEPENING`, `WIDENING`, `SETTLED`. `trend_of` is
  arithmetic, `reading_of` is FR-03's policy, and the split is what lets tone be revised without
  touching a test that pins the numbers.

Left deliberately for `/plan`:

- Rename the `CoverageAssessed` `ToolResult` to `CoverageAssessment`, add the `CoverageAssessed`
  event and the action that records it on the session. Mechanical, touches existing tests.
- `build`, `phase_blocks`, `trend_of` and `reading_of` bodies. The conditionality is written in
  the docstrings; the branching is implementation.
- The deterministic double's `_DEFAULT_SOLID` / `_DEFAULT_SHAKY` — author deferred it.
  `_HANDOFF_LINE` is already answered: it becomes the `handoff` block.
- Whether `CaptureTurn.coverage_confidence` survives now that `CaptureSession.assessments` is
  durable. The reply DTO still carries the float outward, which is a reader the model is not.

## Log

### 2026-09-12 — instruction-vs-tool-prose: what the model is told is split across two domain artifacts — OPEN

The frame treats "the instruction" as the domain's model-facing prose, but `Tool.description`
is model-facing domain prose that already exists and already lives in `domain/capture/graph.py`.
Raised by the author on opening; unresolved.

**Why:** if the instruction abstraction is shaped without answering this, capture ends up with
two unrelated prose channels whose agreement is nobody's invariant — and S-04, which renders
tool definitions, will inherit the ambiguity rather than settle it.

### 2026-09-12 — blocks-shape-tone-tools-shape-capability: the two prose channels stay independent, and a block may not name a tool — ACCEPTED

Supersedes the OPEN entry above for this `idea-id`'s question. The instruction does not receive
the turn's tool set, and the builder's signature has no place for one.

**Why:** the author's reading of provider mechanics is correct — the model is given tool names
and descriptions through a channel of their own and uses them without the system instruction
mentioning them. So the instruction need not enumerate tools. But "need not" is the weak form;
the load-bearing form is the prohibition. A block naming a tool would read as gating that tool,
and it cannot: the phase's `get_tools` is the only thing that decides whether a tool is
offered, and prose cannot take back a capability the provider has already shown. Keeping the
prohibition in the type's docstring is what stops a later author writing "use
`propose_note_topic` first" into a block and believing the withheld case is safe.

**Consequence:** the coherence worry raised as thread 2 on opening dissolves rather than being
guarded. There is no block/tool agreement invariant to enforce, because blocks make no claims
about tools. It also means `frame.md`'s "a block the phase withholds is never rendered and so
can never be acted on" is exactly true for blocks and exactly false for tool capability — see
the next entry.

### 2026-09-12 — coverage-shapes-tone-not-capability: coverage may not remove the consent tool, so the frame's "never sees that as an option" is narrowed — ACCEPTED

`frame.md` claims that at low coverage "the model never sees that as an option at all". It
does see it. `Conversing.get_tools` filters on `session.topic` only
(`backend/src/domain/capture/graph.py:94-102`), and coverage may not be added to that filter:
`CoverageAssessed` pins "gates nothing — no guard reads it at any value, including 1.0"
(`graph.py:173-175`), and FR-03 asks only that coverage influence what the agent says and when
it encourages (`context/efforts/llm-adapter/frame.md`, FR-03).

**Why:** the two halves of that frame sentence rest on different mechanisms, and only the first
one works. Adding the block at high coverage is real and is FR-03 satisfied. Removing the
option at low coverage would require withholding the tool, which FR-03 forbids. Left
unnarrowed, this sentence would either push a coverage guard into `get_tools` — breaking FR-03
— or license an acceptance scenario asserting the model cannot signal consent at low coverage,
which no implementation can make true.

**Consequence:** FR-01 is unaffected. Consent still originates in the user's message and the
agent still never transitions unprompted; a consent signal at low coverage is the agent
reading the user correctly, not the agent moving on its own. `frame.md` stays frozen and this
log carries the narrowing, pending the author's decision on a `/frame` reopen.

### 2026-09-12 — instruction-guard-is-type-level: the completeness guard is a property of the type, not of the builder being the only path — ACCEPTED

`Instruction` carries `required` as a field and validates in a `model_validator`, so every
construction path enforces FR-05.

**Why:** `frame.md` reasoned that the guard's strength depends on the builder being the sole
construction path, and carried that as a live risk. Carrying the required set on the
instruction removes the dependency — there is no construction path that yields an incomplete
instruction, so nothing is left for a caller who declines to use the builder to step around.
It also matches how this repository already enforces declaration invariants: `Graph._validate_edges`
and `Tool._result_discriminator_matches_name` both refuse a malformed declaration at
construction (`backend/src/domain/shared/graph/model.py:74-82,236-250`).

**Consequence:** the builder no longer has to be defended as exclusive, which is a weaker thing
to maintain. The duplication of `required` on both builder and instruction is carried as thread
2 in `## Current State`.

### 2026-09-12 — three-channels-instruction-is-the-remainder: the transcript is not a block, for the same reason a tool is not — ACCEPTED

Generalises `blocks-shape-tone-tools-shape-capability`. The model is reached through three
channels — instruction, tool schemas, message history — and the instruction carries only the
remainder once the other two are subtracted.

**Why:** the author's argument about tools was not really about tools. It was that a channel
the provider already serves natively must not be duplicated in prose, because the duplicate
cannot gate and can only disagree. Message history is the same case: `_prompt_and_history`
(`backend/src/adapters/out/llm/capture/agent.py:124-133`) already hands the exchange over as
history, so a block restating it would be a second, staler copy of the conversation.

**Consequence:** the rule is now stated once at the type rather than as a fact about tools, so
a fourth channel a provider adds later lands on the same side of it without re-litigating.

### 2026-09-12 — block-may-state-ordering: the tool prohibition covers the tool's identity, not its subject — ACCEPTED

Refines `blocks-shape-tone-tools-shape-capability`, which as first written would have banned
prose about work a tool performs.

**Why:** drafting has a real ordering constraint that only prose can carry. Appending content
to a draft with no topic raises `DraftTopicMissingError`
(`backend/src/domain/capture/graph.py:373-374,386-387`), and `Drafting` does not filter its
tools at all (`graph.py:121-170` declares no `get_tools` override), so all four note tools are
offered every turn with nothing saying which comes first. A `Tool.description` cannot state it
either: ordering is a relation between tools, and no single description owns it.

**Consequence:** "Name its topic before writing its body" is the drafting `task` block's
closing sentence, and it names no tool. The line to hold is that a block states the work, never
the identity of the thing that performs it.

### 2026-09-12 — requiredness-follows-silence: a block is required iff its subject is never silent — ACCEPTED

The test for whether a block belongs in a phase's required set: is there always something true
to say about its subject? If yes, it is required and its text varies. If it is sometimes about
nothing, it is optional and absent then.

**Why:** without a test, requiredness becomes taste, and FR-05's guard is only as meaningful as
the set it checks. It also resolves the case that looked hardest: `draft_state` is required even
though the draft may be empty, because the empty draft is precisely the state the model most
needs told — that is where the ordering failure lives. Conversely `session_topic` is optional,
because before the session is named the exchange already shows it is new and a block saying so
adds nothing.

**Consequence:** `Conversing.required` is `{task, language}` and `Drafting.required` is
`{task, language, draft_state}`. `coverage_trend` is optional, which means FR-03's
load-bearing block is one the phase may withhold — correct on the first turn, when no trend
exists, and the reason thread 4 matters.

### 2026-09-12 — no-later-filter: withholding happens while building, never after — ACCEPTED

`Instruction.blocks` is exactly what the model is told. A phase decides what to withhold as it
builds; nothing filters, masks or hides a block afterwards.

**Why:** a second gating step is the one way FR-05's guard can be defeated. A required block
could be present at construction, satisfy `required`, and then be suppressed on the way to the
adapter — and the guard would have passed on an instruction that never reached the model
intact. Raised by the author as "what if it wants to hide blocks"; the answer is that hiding and
withholding are the same act performed at different times, and only the earlier time is sound.

**Consequence:** this was not merely a rule to state — the type did not hold it. `blocks` was
`Sequence[InstructionBlock]`, which pydantic stores as a list, and `instruction.blocks.append(...)`
succeeded on a validated instance (probed in-session), so a validated instruction could have
its required block removed afterwards. The field is now `tuple[InstructionBlock, ...]` and
post-construction removal raises. `frozen=True` alone was not enough, because it freezes field
rebinding and not the container behind the field.

### 2026-09-12 — blocks-are-decided-as-a-set: inter-block dependence needs no new mechanism — ACCEPTED

A block's presence, and its text, may depend on which other blocks are there. No prerequisite
declaration, no per-block predicate, no priority ordering is added for it.

**Why:** `build(context) -> Instruction` already returns the whole instruction at once, so the
decision is over the set by construction. This codebase has already argued the same point for
tools and chose the same shape: `State` declares an inventory and decides per turn with a
method, "because eligibility is a statement about the phase as a whole — a state may withhold
one tool because another has already done its work, which a list of independent predicates
cannot express" (`backend/src/domain/shared/graph/model.py:85-97`). Declaring block
prerequisites as data would be exactly the list of independent predicates that reasoning
rejected, adopted one layer up.

**Consequence:** the author's "additive" reading of the instruction was never forced by the
shape — it was an accident of how the inventory table reads, with one predicate per row. The
table stays a summary of the common case; the builder's docstring is where a dependence between
two blocks is stated when one exists. Nothing in capture needs one yet, which is why none is
written.

### 2026-09-12 — requiredness-is-static: a required set computed from the turn would be a tautology — ACCEPTED

`InstructionBuilder.required` is a property with no context and stays that way. A block that
is only indispensable in some states must choose a side: required always, with text that
handles the dull case, or optional, with absence that is not an error.

**Why:** if requiredness were computed from the same context that decides presence, a builder
could always make the two agree, and FR-05's guard would pass by construction on every
instruction it ever built. "Required" would decay into "whatever I decided to include". It
would also cost the property `State.tools` is deliberately given: what a phase can promise,
inspectable without a context (`backend/src/domain/shared/graph/model.py:99-104`).

**Consequence:** `draft_state` pays this price explicitly — required in drafting even when the
draft is empty, because the empty draft is a state with something true and important to say.
There is no third option, and that is the cost of FR-05 meaning anything.

### 2026-09-12 — general-part-is-capture-wide: the floor is required of the flow, not of each phase — ACCEPTED

Raised by the author: the general part must be required. Taken in its stronger reading — the
general part is required *of capture*, so a phase is not given the choice to drop it.
`CaptureInstructionBuilder` declares `required` as `{FLOW, LANGUAGE} | phase_required` and a
subclass supplies only `phase_required`.

**Why:** had each phase declared its own flat required set, dropping the general part would
have been a matter of not writing it — discouraged, not unavailable, which is the weaker form
this session has refused everywhere else. The union makes subtraction inexpressible, and a
phase added later inherits the floor without anyone remembering.

**Consequence:** the general part gained a block that does not exist today. `FLOW` — what a
capture session is for, and that it belongs to the user throughout — has no counterpart in the
current prose: both constants at `backend/src/adapters/out/llm/capture/agent.py:48-56` open
straight at "Continue this capture conversation", so the model is never told what capture is.
The general/phase line is what surfaced it: `language` alone would have been a thin floor, and
asking what else is true of capture in every phase produced the missing preamble. `TASK` sits
on the phase side, since conversing and drafting ask for different work.

### 2026-09-12 — coverage-falls-too: the trend is three-valued and FLAT is a band — ACCEPTED

`CoverageTrend` is `RISING | FLAT | FALLING`, derived over the most recent
`COVERAGE_TREND_WINDOW` assessments, with movement under `COVERAGE_FLAT_BAND` counting as no
direction at all.

**Why:** the author's point that coverage can fall is not an edge case, it is a normal capture
move — a user who opens new ground mid-session makes the topic larger, so the honest judgement
of how much is covered drops. A two-valued trend would have to call that either progress or
no-change and both are false. The band is the other half: without it every reassessment
registers as a direction, `RISING` becomes almost always true, and the word stops carrying
information. A band is what makes "coverage is rising" a claim a test can fail.

**Consequence:** `COVERAGE_FLAT_BAND` and `COVERAGE_TREND_WINDOW` are named domain constants,
not numbers inside a formula. The window also separates two decisions `frame.md` had fused:
the session keeps *every* assessment because a discarded one is unrecoverable, and a reading
looks at *recent* ones because the opening turns must not outvote the present one forever.

### 2026-09-12 — trend-is-arithmetic-reading-is-policy: two derivations, not one — ACCEPTED

`trend_of(assessments) -> CoverageTrend` and `reading_of(assessments) -> CoverageReading | None`
are separate, in `domain/capture/coverage.py`.

**Why:** they fail for different reasons and are revised by different people. Which way the
numbers went is arithmetic and can be pinned by a test without anyone agreeing on tone; what
the agent should do about it is FR-03's judgement and is the part the author will want to
revise after using the thing. Fused into one function, every change of tone would edit code
that a trend test also depends on.

**Consequence:** `reading_of` returns `None` for an empty history, which is the whole of the
`coverage_trend` block's optionality — a single assessment is enough, because a level alone
already separates `EARLY` from `SETTLED`. That closes thread 4 as it stood: the reading uses
the level *and* the trend, so it exists from the first assessment rather than the second.

### 2026-09-12 — four-coverage-readings: EARLY, DEEPENING, WIDENING, SETTLED — ACCEPTED

The closed vocabulary the instruction speaks. `frame.md` names two of them directly — climbing
turns the tone towards closing (`DEEPENING`), flat and low affirms keeping the session open
(`EARLY`). The other two are what that sentence leaves out: `SETTLED` is flat and *high*, where
little new is arriving and closing should be encouraged, and `WIDENING` is falling, where the
drop must not be read as lost progress.

**Why:** each member has a distinct thing to be encouraging about, which is the test for
whether it earns a place. `SETTLED` and `DEEPENING` both lean towards closing but differently —
one says we are there, the other says we are getting there — and `WIDENING` is the only reading
that actively suppresses the closing question. Four, not the six a level × trend product would
give, because a falling coverage from a high level and from a low one call for the same thing.

**Consequence:** being a closed `StrEnum` buys the exhaustiveness this repository already
recovers by test elsewhere (`context/foundation/rules/exceptions.md`): a suite walks every
member and asserts it has prose, so a reading added later cannot reach the model as a word with
nothing behind it.

### 2026-09-12 — coverage-is-a-value-object: the float the model sends is range-guarded — ACCEPTED

`Coverage` is a frozen value object refusing anything outside `[0.0, 1.0]` and anything
non-finite, raising `CoverageOutOfRangeError`.

**Why:** the model supplies this number. `CoverageAssessed` currently carries a bare float
(`backend/src/domain/capture/graph.py:173-178`) whose only validator is pydantic's float
coercion, so `7.3` or a NaN would pass the tool, reach the session, and be inherited silently
by the trend arithmetic — a NaN in particular makes every band comparison false and would read
as `FLAT` forever. It also follows the shape `SimilarityScore` already uses for the same
problem (`domain/capture/value_objects.py:136-146`).

### 2026-09-12 — interpolation-belongs-to-the-block: prose carries its values inside the sentence — ACCEPTED

`InstructionBlock.rendered(name, template, **values)` interpolates and keeps only the result.
Chosen by the author over the alternative of keeping prose literal and shipping the value as a
separate field beside it.

**Why:** the author's reason was that it stays testable while being more flexible, and the
flexibility is the real argument — where a topic name reads well inside a sentence is a
decision the phase's prose author has to make per block, and a fixed arrangement ("the value
follows below") makes that decision once for prose it has never seen. Testability is preserved
because the template is a module constant a test asserts against and the rendering is pure.

**Consequence:** testability is preserved *only because of the guard*, not because of the
templating. `rendered` refuses a template whose placeholders are not exactly the keys supplied,
in both directions, and refuses positional placeholders. Without it a renamed placeholder
yields a block that is silently half-prose and the only reader that would notice is the model.
The guard was verified in-session against a renamed placeholder, an unused value, and `{}`.

**Consequence:** the block keeps neither template nor values — it renders at construction and
stores `text` alone. This is the `Instruction.blocks` tuple lesson applied again: nothing is
left behind that a later edit could change the rendered prose through. Constructing a block
with literal `text` stays available and is not a bypass, because prose with no placeholder has
nothing to mismatch.

### 2026-09-12 — prose-lives-in-constants-not-in-build: a builder picks prose, never writes it — ACCEPTED

Templates are module constants beside the literal blocks, and `_COVERAGE_READING_PROSE` maps
each `CoverageReading` to its prose. A builder selects and supplies values; no authored prose
appears inside `build`.

**Why:** an f-string inside `build` would put domain prose back inside construction logic,
which is precisely the entanglement this change exists to undo — today's instructions are
selected by an `if` on the phase inside the adapter
(`backend/src/adapters/out/llm/capture/agent.py:118-121`). Moving that `if` from the adapter
into a domain builder and leaving the prose inside it would move the smell rather than remove
it.

**Consequence:** the split the session had been carrying as one open thread is now two, and
only one was ever a problem. Selection from a closed set (`coverage_trend`'s four readings) is
just constants being chosen and needs nothing. Interpolation is the genuinely new mechanism and
is the only thing `rendered` exists for.

### 2026-09-12 — build-is-final: the builder's required set and the instruction's cannot disagree — ACCEPTED

`CaptureInstructionBuilder.build` and `.required` are `@final`. A phase overrides
`phase_blocks` and `phase_required` and never the composition.

**Why:** this closes the duplication the session had carried open since `required` was placed
on both the builder and the instruction. Two copies of one fact are only safe while nothing can
write them apart, and a phase free to build its own `Instruction` could have passed a required
set that disagreed with the one it advertises — the guard would then have checked an
instruction against a declaration no other reader holds, which is a guard passing on its own
say-so. Composing in one final place means the two are the same value rather than two values
that happen to match.

**Consequence:** the mirror to `State.tools` / `State.get_tools` holds properly now. There the
inventory is inspectable without a context and the filtered set is derived from it; here
`required` is inspectable without a context and the built instruction is derived from it, with
no path that derives something else.

### 2026-09-12 — frame-override: this session supersedes frame.md on coverage and capability — ACCEPTED

Recorded at the author's instruction on closing, and stated once here so no reader has to
reconstruct it from three entries. Where this log and `frame.md` disagree, the log is later and
governs. The disagreement is one sentence and one only: everything else in the frame's body
stands unamended.

**Why:** the author chose the override over a `/frame` reopen. The frame's claim rests on a
mechanism that does not exist — prose cannot withdraw a tool the provider has already shown the
model — and reopening the frame to fix one sentence would cost a session to record what this
log already records with its full reasoning. The risk the author accepts is that a reader who
opens `frame.md` and not this log believes the unamended sentence; the mitigation is that the
override is stated in `## Current State`, which is the first thing any reader of this pair sees.

**Supersedes:** the `## Boundaries` sentence "high coverage adds the block that lets the agent
say it is ready to draft, and at low coverage the model never sees that as an option at all"
— its first clause only. The second clause is void.

