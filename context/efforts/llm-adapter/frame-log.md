## Current State

Session closed. `frame.md` is frozen and is the governing document for this effort — it
holds the thesis, the boundaries, and `FR-01`..`FR-09`. Nothing at frame altitude is still
contested. What follows is only what is genuinely still open, for whoever picks this up.

**Parked, awaiting a later decision:**

- **Langfuse deployment** — cloud vs self-hosted Compose. Deferred to the observability
  work pending a cost calculation. Cloud bills per span and agent traces with tool calls
  produce many; self-hosting is free but wants ~4 vCPU / 16 GiB (`research-langfuse.md`).
  The estimate depends on span volume per turn, which the agent-design slices determine —
  so this slice should come after them.
- **Handoff between agents** — neither adopted nor ruled out. `frame.md` carries the
  non-foreclosure constraint and its intended reading: model phases and transitions, do not
  model agents yet.
- **Evaluation** — out of scope here, revisitable once `FR-08`'s prototype exists as the
  baseline it would measure against.

**Left to `/plan`, as mechanism under requirements already settled:**

- `CardGeneration`'s shape — one shot returning a list, or per-card tool calls that return
  the `CardFactory` verdict to the model. This decides whether `distill` joins the
  tool-and-graph half of the domain module or stays on the instruction half alone.
- Where the `FR-05` guard runs, and therefore who assembles the instruction: the
  application command (every port signature changes, and `send_message.py` with them) or
  the adapter (ports unchanged, enforcement weaker).
- Which types a context requirement is expressed over, given that `Transcript` and
  `ConfidenceAssessment` are application objects today.
- Whether the transition graph holds a per-turn call budget.
- Whether conversational mode is persisted on `CaptureSession` or transient in the agent
  loop.

**Known friction, accepted:** `context/adrs/capture-flow-domain-shape/decision.md` states
that tool-call mechanics stay out of the domain model, and fixes a `CaptureSession` with no
conversational phase. No ADR is being written; this frame governs, and the ADR text is
narrower than it first reads — it concerns persistence of tool-call mechanics in the
aggregate model, not where policy lives.

**Highest technical risk to `FR-09`:** streaming interleaved with tool calls, the most
framework-specific surface in reach and the place a pydantic-ai shape is likeliest to leak
into the domain.

## Log

### 2026-09-11 — session-open: Frame opened on the llm-adapter effort — OPEN

Effort container already held three research documents and an empty Goal. The user
declined both `/prd` and `/bdd` for this effort, so `frame.md` is the only
requirement-bearing document the downstream chain will read.

**Why:** A technical effort with no PRD and no acceptance criteria has no other place
to record what must be true when it is done.
**Consequence:** Requirements here mint `FR-nn` rather than citing `AC-nn`.

### 2026-09-11 — domain-abstraction-layer: LLM abstractions proposed for the domain layer — OPEN

The stated framing places abstractions over the LLM adapter — named as *tool calls* and
*instructions* — in `domain.shared`, with concrete children in `domain/capture` and
`domain/distill`.

**Why OPEN, not REJECTED:** the claim is ambiguous between domain-vocabulary policy
(defensible) and prompt/tool-schema material (not). Evidence bearing on it:

- All five LLM-facing seams live in the **application** layer today, not the domain:
  `backend/src/application/capture/ports.py:21-36` (`TopicExtractionPort`,
  `ConfidenceAssessmentPort`, `ReplyGenerationPort`, `EmbeddingPort`) and
  `backend/src/application/distill/ports.py:9-10` (`CardGeneration`).
- The domain's own `ports.py` files are persistence-only:
  `backend/src/domain/capture/ports.py`, `backend/src/domain/distill/ports.py`.
- `context/foundation/rules/layering.md:16-18` — domain has zero adapter-facing imports,
  `pydantic-ai` named explicitly; echoed at
  `context/adrs/hexagonal-arch-shape/decision.md:18`.
- Precedent for a domain-held `Protocol` plus a concrete implementation exists:
  `backend/src/domain/distill/note_format.py` (`NoteFormat` / `MarkdownNoteFormat`) —
  but it is deterministic text handling in the domain's own vocabulary, not a model
  concern.
- `domain/shared/` today holds only the outbox (`backend/src/domain/shared/outbox/`),
  so this would be its second tenant.

### 2026-09-11 — domain-abstraction-layer: Domain owns LLM behaviour policy — ACCEPTED

Reading (A) confirmed and reaffirmed by the user: the application is not pretended to
make sense without LLMs, so conversational and language-understanding policy is product
substance, not infrastructure. Instructions are adapter-independent and belong to the
domain; tool calls *execute* in the adapter while their *configuration* is domain
material. Application ports are transport and were never intended to hold this.

**Why — the objection did not survive the evidence.** The layering rule forbids the
domain importing `pydantic-ai` (`context/foundation/rules/layering.md:16-18`); it does
not forbid the domain holding policy expressed in its own vocabulary. And the current
arrangement demonstrates the cost of the alternative: capture's entire socratic
conversation strategy is today hard-coded inside an adapter —
`backend/src/adapters/out/in_memory/capture/reply_generation.py` holds
`_CONFIRMATION_PHRASES` (the rule for when a session may draft its note),
`_HANDOFF_LINE`, and the reply template `"You've got a handle on: {solid}. Let's dig
into: {shaky}."`, plus `_derive_topic_label` / `_derive_tag_labels` deciding what a
topic and tag are. None of that is visible to `domain/capture/`. Swapping to an LLM
adapter would rewrite that policy from scratch in a second adapter, with nothing to keep
the two honest.

**Consequence:** Boundary written into `frame.md`. The seam is *what is instructed*
(domain) against *how it is rendered and invoked* (adapter under `adapters/out/llm/`).

### 2026-09-11 — policy-vs-verdict: Steering and judging are different instruments — OPEN

"Abstractions over the adapter" conflates two mechanisms with very different testability,
and `distill` and `capture` sit on opposite sides of the split today.

**Why it matters.** `distill` already lets the domain govern model output *after the
fact*: `CardGeneration` returns a bare `CardProposal` (`front`, `back`, `quote` —
`backend/src/application/distill/value_objects.py`), and the domain then judges it.
`CardFactory._verdict` (`backend/src/domain/distill/card_factory.py`) discards a proposal
as `UNGROUNDED` when its anchor does not resolve and as `OVERSIZED` when
`CardLengthPolicy` is breached, and `Card` itself rejects identical sides
(`backend/src/domain/distill/card.py`, `IdenticalCardSidesError`). That is domain
authority over an LLM, enforced by ordinary unit tests on every CI run.

`capture` has no counterpart. `ConfidenceAssessment` and the `ReplyChunk` union
(`backend/src/application/capture/value_objects.py`) carry only field-level validation —
non-empty note, `coverage_confidence` in `[0.0, 1.0]` — and cross the seam with no domain
verdict at all.

**The open claim:** an `Instruction` held in the domain is constrained by no test, so it
gains the domain's location without the domain's guarantees; a verdict held in the domain
is constrained on every run. Both are probably wanted, but they must not be confused, and
the testability question is what decides whether Langfuse evaluation enters this effort's
definition of done.

### 2026-09-11 — draft-tool-call: The draft handoff is the first concrete tool call — OPEN

The user named `generate` as the sure-thing tool call, pointing at the in-memory
adapter's heuristics. Confirmed in code and traced end to end.

**What the heuristic is.** `DeterministicReplyGenerationAdapter.generate`
(`backend/src/adapters/out/in_memory/capture/reply_generation.py`) branches on
`_should_draft(transcript)`, which is true when the last user message matches
`_CONFIRMATION_PHRASES` — a fixed set of six strings ("that's all", "we're done", …).
On that branch it stops conversing and emits `DraftTopicChunk`, `DraftTagChunk`, and
`DraftContentChunk`. As a tool call, the model would invoke a draft capability with topic
label, tag labels, and note content instead of the string match deciding.

**Why OPEN — it cuts against the principle just accepted.** Whether a capture session has
been explored enough to become a note is exactly the kind of policy the
`domain-abstraction-layer` entry placed in the domain. Handing it to the model as a tool
call moves it *further* out: the decision would travel model → adapter → the `saw_draft`
flag at `backend/src/application/capture/commands/send_message.py:105,115,127`, and reach
`session.draft_note` at :149 without any domain rule having judged readiness.

**What the domain guards today, and what it does not.**
`CaptureSession.draft_note` (`backend/src/domain/capture/capture_session.py:45-57`)
guards *lifecycle* only — session open, note not already drafted. There is no readiness
rule. Meanwhile `coverage_confidence` — the domain's own explicit measure of how fully the
topic is covered — decides nothing anywhere: `grep -rn coverage_confidence backend/src/`
returns only its definition (`application/capture/value_objects.py:45`), its DTO field
(`application/capture/dto.py:33`), a hard-coded `0.0` in the deterministic adapter, and a
pass-through into `ReplyDoneEvent` (`send_message.py:167`). It is pure telemetry.

**The resolution on the table:** the tool call is a *request to draft*, and the domain
holds the readiness verdict that decides whether to honour it — which would make
`coverage_confidence` load-bearing and give `capture` the `CardFactory._verdict`
counterpart it lacks. Not yet decided.

**Second tool call, unnamed.** Strongest candidate in the code is vocabulary lookup:
today `VocabularyResolver.resolve_topic` / `resolve_tag`
(`backend/src/application/capture/services/vocabulary.py:17-33`) reconcile the model's
freely-invented label against existing entries *after the fact* via `EmbeddingPort` and
`MatchCriteria.best_match`. A tool would let the model see existing topics and tags and
reuse one deliberately. Awaiting confirmation.

**Risk carried from prior research.** `research-pydantic-ai.md` records that with a
non-text `output_type`, `run_stream` may stop at the first final output. `ReplyGeneration`
is a streaming port whose tool call must interleave with streamed reply text
(`send_message.py:100-131` consumes one `async for` over mixed chunk kinds), so this is
the port where that caveat bites hardest.

### 2026-09-11 — draft-tool-call: Coverage steers the instruction; the user decides — ACCEPTED

`coverage_confidence` is an **input to the instruction**, not a gate. It shapes what the
agent says and how strongly it encourages moving to a note; the decision itself stays with
the user. The tool call's job is to recognize the user's consent in natural language —
which is exactly what `_CONFIRMATION_PHRASES` does today and does badly, matching six
fixed strings.

**Why this supersedes the readiness-verdict proposal.** The earlier entry
(`draft-tool-call`, OPEN, this date) put a domain *readiness verdict* on the table as the
resolution. Rejected in that form: the domain does not judge whether the session is ready,
because that judgement is the user's. What the domain keeps is **legality** — which
transitions are allowed from which state — the same kind of guard
`CaptureSession.draft_note` already holds (`backend/src/domain/capture/capture_session.py:51-54`).

**Consequence:** a three-way split, now the frame's working model — the user grants
permission, the model recognizes it, the domain guards that the transition is legal.
`coverage_confidence` becomes load-bearing via the instruction rather than via a gate.
Settled as `FR-01` and `FR-03`.
**Supersedes:** the readiness-verdict resolution proposed in `draft-tool-call` above.

### 2026-09-11 — conversation-mode: Capture has no mode machine anywhere — OPEN

The user names the real gap: transition into note-generation mode **and back to capture**,
which the in-memory adapter has no notion of — and which would be absurd to write there.

**Why it is a genuine gap, not an oversight in the adapter.** The aggregate has no mode.
`CaptureSession` is `id`, `topic`, `note_id`, `status` (`open` | `closed`), `created_at`
(`backend/src/domain/capture/capture_session.py:23-28`), and `status` means specifically
"approved, note sent" per `context/adrs/capture-flow-domain-shape/decision.md` — not a
conversational phase. The adapter is stateless per turn: `_should_draft` re-evaluates the
last user message on every call and nothing remembers that a draft is underway.

What *does* exist is the redraft loop — `Note.update_content` / `change_topic` /
`add_tag` / `remove_tag` guarded on `status == draft`, driven by
`GenerateReplyCommand._apply_redraft` (`send_message.py:175-198`) per US-06/AC-13. So
returning to capture and drafting again is supported at the *aggregate* level. What is
missing is the conversational phase concept above it.

**Why this argues for the user's own position.** If mode lives in the adapter, every
adapter reinvents it and the in-memory one has to grow a mode machine to satisfy the
contract — which is the absurdity named. If mode is domain state, the in-memory adapter
stays trivial and InMemoryFirst (`context/foundation/rules/layering.md`) survives intact.
The "it would be absurd to write it there" instinct is the layering rule pointing at the
domain.

**Open:** is mode a field on `CaptureSession` (persisted, and therefore an amendment to a
settled ADR's aggregate shape), or a transient phase the agent loop carries within a turn?
`FR-02` fixes the requirement without yet fixing the mechanism.

### 2026-09-11 — adr-tool-call-exclusion: A settled ADR excludes tool calls from the domain — OPEN

`context/adrs/capture-flow-domain-shape/decision.md` states, under `Message`:
"Tool-call mechanics the agent runs while probing understanding (US-01) stay out of the
domain model entirely; no story asks for them to be persisted."

**Why it is raised rather than treated as fatal.** The ADR sentence is about *persistence*
of tool-call mechanics in the aggregate model, which is narrower than this frame's claim
that tool-call *configuration* is domain policy. The two can be read as compatible. But
the wording is close enough that `/roadmap` and `/plan` will hit it, and the same ADR fixes
a `CaptureSession` shape that `conversation-mode` may need to amend.

**Consequence:** this effort probably owes an ADR — either a narrow amendment to
`capture-flow-domain-shape` or a new one for the LLM-policy layer. Not decided here; noted
so it is not discovered late.

### 2026-09-11 — agent-handoff: Handoff between agents is a bigger abstraction than instructions — OPEN

The user raises handoff to another agent as a possible mechanism for the mode transition,
alongside instruction and tool call.

**Why it widens the frame.** The accepted boundary says the domain holds instructions and
tool configuration. A handoff is neither: it is a statement that *a different agent, with a
different instruction and a different tool set, takes over the turn*. If handoff is in, then
`domain/shared/` holds an agent-and-handoff abstraction, not just instruction-and-tools —
a materially larger domain module than the one stated when this session opened.

It also collides with the port shape. One port is one model call today:
`ReplyGenerationPort.generate` yields a single mixed stream consumed by one `async for`
(`send_message.py:100-131`). A conversation agent handing off to a drafting agent and back
would hide a multi-agent loop behind that single port — invisible to the domain, which is
the arrangement this frame just rejected for conversation policy.

**Open:** is handoff a real candidate for this effort, or the third option listed for
completeness? If real, does the domain see the agents, or only the modes?

### 2026-09-11 — policy-vs-verdict: Context completeness is the deterministic guard on an instruction — ACCEPTED

The open objection was that a domain-held `Instruction` is constrained by no test, so it
gains the domain's location without the domain's guarantees. Answered, and on its own
terms: the instruction's **required context** is a deterministic invariant. Whether the
model receives everything the task needs is checkable without a model, and it is important
enough to be an invariant rather than a convention — what belongs in the context for a
given adapter task is a property of the task, not of the provider.

**Why it closes the objection.** It supplies the third thing the domain was missing.
Transition graphs are classically unit-testable; tool configuration is data; and the
instruction — the piece that looked untestable — carries a precondition that is
deterministically enforceable. That is the same *kind* of authority
`CardFactory._verdict` holds over `CardProposal`
(`backend/src/domain/distill/card_factory.py`), applied before the call instead of after.
The stated purpose of the whole placement is maximizing the surface reachable by unit
tests, and this is what makes the surface reachable.

**Consequence:** settled as `FR-04` and `FR-05`, with the three domain tenants written
into `frame.md`'s Boundaries.

**Limit, recorded deliberately.** The guard proves *presence*, not *sufficiency* — a
complete context can still carry a useless instruction. So this does not close the
evaluation question; `frame.md` now says so out loud under Out of scope, and the Langfuse
thread stays live.

### 2026-09-11 — context-guard-placement: The context invariant forces two open forks — OPEN

`FR-05` is not free. Two questions it makes decidable, neither yet decided.

**Which types the requirement is expressed over.** The context capture's reply instruction
needs is `Transcript` and `ConfidenceAssessment` — both **application** value objects
(`backend/src/application/capture/value_objects.py`), with `Transcript` assembled by a
CQRS read path (`backend/src/application/capture/queries/transcript.py`,
`send_message.py:90`). Their constituents are domain types (`MessageContent`,
`MessageRole` from `domain/capture/value_objects.py`), but the assembled shapes are not. A
domain instruction that names its required context therefore either pulls those shapes down
into the domain, or expresses the requirement abstractly enough not to name them. The first
is a real move with persistence and query implications; the second risks a guard that
cannot actually check what it claims.

**Where the guard runs — which settles who assembles the instruction.** If the application
command assembles the instruction and passes it into the port, the guard runs in the
application and every port signature changes, along with `send_message.py`. If the adapter
pulls the instruction from the domain, ports stay as they are and only `compose.py` wiring
changes — but enforcement then lives in the adapter, which is the layer this frame has
spent the session moving authority *out of*. The invariant argues for the first; the first
is the expensive one. Naming it now so `/roadmap` does not inherit it unexamined.

### 2026-09-11 — vocabulary-tool-call: Vocabulary lookup confirmed as the second tool call — ACCEPTED

The model looks existing topics and tags up and reuses one deliberately, instead of
inventing a label that `VocabularyResolver` then reconciles after the fact.

**Why.** Today `resolve_topic` / `resolve_tag`
(`backend/src/application/capture/services/vocabulary.py:17-33`) take whatever label the
model emitted, embed it, and run `MatchCriteria.best_match` against candidates — reuse is
something the *system* infers from a similarity score, never something the model chose.
The ADR describes this as reconciliation happening at draft time
(`context/adrs/capture-flow-domain-shape/decision.md`). A lookup tool moves reuse from
inference to intent.

**Consequence for `EmbeddingPort` (open thread 9):** this does not retire the embedding
path — candidates still have to be found by similarity to be shown — but it changes its
role from adjudicator to retriever. Whether that keeps `EmbeddingPort` in this effort is
still open.

### 2026-09-11 — card-generation-split: Card generation may be many tool calls, not one shot — OPEN

Raised by the user, uncertain whether a single shot produces acceptable cards. The code
gives the split a strong structural argument, and one the frame did not previously have.

**What one-shot costs today.** `CardGeneration.generate(content) -> list[CardProposal]`
returns everything at once, and `GenerateCardsCommand.handle`
(`backend/src/application/distill/commands/generate_cards.py:49-68`) then judges each
proposal alone: it builds `NoteDocument.of(note.content)`, resolves each `Anchor` via
`document.locate`, mints through `CardFactory`, and **saves the card even when the verdict
discards it** (`:60-63` — `uow.cards.save(card)` runs regardless of `card.discard`).
A proposal that raises is logged and skipped (`:64-68`). Either way the model never learns
that its quote did not anchor or that the card was oversized. The domain's verdict is
one-way.

**What the split buys.** Per-proposal tool calls make `CardFactory._verdict` a *tool
result*: the model proposes a card, the domain judges grounding and length, and the
judgement returns to the model, which can re-anchor and retry. The domain authority already
exists and is already unit-tested; what it lacks is a feedback channel, and tool calls are
that channel. The block machinery to iterate over is already domain-side too —
`NoteFormat.blocks()` / `normalize()` (`backend/src/domain/distill/note_format.py`) and
`NoteDocument`.

**Why it stays OPEN.** Whether one shot suffices is an empirical question this frame cannot
settle by argument — which is itself evidence for open thread 6: without evaluation there
is no way to answer it except by impression. It also multiplies model calls per note, which
bears on cost and on the worker path (`FlashcardGenHandler`).

### 2026-09-11 — domain-command-centre: The domain is the command centre over the LLM — ACCEPTED

The effort's thesis, stated by the user and written into `frame.md`'s Boundaries: build a
command centre around the domain over the LLM. Tool calls speak the domain's language, and
the domain exposes the functions the model invokes — preferably side-effect-free.

**Why accepted.** It is the general form of the pattern the previous three entries arrived
at separately (`draft-tool-call`, `vocabulary-tool-call`, `card-generation-split`): each
one is a domain verdict that currently travels one way, given a return path. Naming it as
one thing makes `domain/shared/` hold a tool abstraction rather than three unrelated
shapes. Settled as `FR-06`.

### 2026-09-11 — pure-tools: "Side-effect-free" holds for two tools and breaks on the third — OPEN

`FR-06` says tools invoke domain functions. The *purity* preference does not survive
contact with all three candidates, and where it breaks is informative.

**Card verdict — pure, and already written.** `NoteDocument.of(content)` then
`document.locate(anchor)`, then `CardFactory.mint` → `_verdict`
(`backend/src/domain/distill/{note_document,card_factory}.py`). Given the note content,
judging grounding and length is a pure function of its arguments. Nothing to change but the
direction it is called from.

**Vocabulary lookup — not pure as stated, and the fix is load-bearing.** "Look up existing
topics" needs `topics.candidates()` (a repository read) and `EmbeddingPort.embed` (an LLM
adapter call) — see `backend/src/application/capture/services/vocabulary.py:17-39`. That is
an application service over two ports, not a domain function, so as written it violates
`FR-06`. It becomes pure only if the candidates are already *in the context*: the tool then
reduces to `MatchCriteria.best_match`, which is domain
(`backend/src/domain/capture/vocabulary.py`) and pure.

**Consequence, and it unifies two requirements.** If tools are pure domain functions, their
inputs must arrive through the context — which is exactly what `FR-05` guards. Retrieval
stays in context assembly; the tool only decides. `FR-05` and `FR-06` are then two halves of
one mechanism rather than two rules.

**Draft transition — cannot be pure.** Drafting mutates `CaptureSession` and creates a
`Note` (`capture_session.py:45-57`), and persistence belongs to the application's
`UnitOfWork`. An effect-bearing tool is unavoidable here.

**The open fork:** are tools split into *queries* (pure domain functions, freely callable)
and *commands* (effectful, bounded by the transition graph and the application's
transaction boundary)? That split would mirror the CQRS-lite line the repo already draws
(`context/adrs/capture-flow-domain-shape/decision.md` — application-owned `UnitOfWork`
commit boundary, queries reading straight into DTOs). Not decided.

### 2026-09-11 — tool-ordering: Effectful tools make `FR-04`'s graph load-bearing — OPEN

A consequence of letting the model call effectful domain functions, not yet weighed.

**The existing evidence that ordering already bites.** `GenerateReplyCommand.handle` raises
`DraftTopicMissingError` when a tag or content chunk arrives before a topic chunk
(`backend/src/application/capture/commands/send_message.py:116-117, 128-129`) — an ordering
invariant the application already has to enforce against a stream the model controls. Tool
calls widen that surface rather than narrowing it: the model can invoke in any order, any
number of times.

**Why it is sharper than it looks.** The whole `async for` runs inside
`async with self._uow` (`send_message.py:77-169`), so a model calling an effectful tool is
writing inside an open transaction, mid-stream. Repeated or out-of-order calls are writes,
not just bad output.

**Consequence:** the transition graph settled as `FR-04` is not only a conceptual model of
conversational phase — it is the thing that has to constrain which tools are invocable
when, and how often. That is an argument for the graph being real, enforced code rather
than documentation, and it is the strongest structural reason yet that the graph belongs in
the domain.

### 2026-09-11 — evaluation-scope: Evaluation is deferred until a prototype exists — PARKED

Not rejected — deliberately deferred. The user's reasoning: this is a new tool at MVP
stage, evaluation is expensive, and it is too expensive for a project this young. It can
arrive later, once there is a baseline to measure — a working LLM-backed prototype.
Quality in the meantime is judged empirically, by using the thing.

**Why PARKED is the right tag.** The need was never disputed; the timing was. Evaluation
has a precondition (a prototype) that this effort exists to produce, so it cannot precede
it.

**Consequences, recorded so they are not lost.**

1. `card-generation-split` cannot be settled by measurement inside this effort. One-shot vs
   per-card tool calls becomes a judgement call, revisited once the prototype is in use.
2. `FR-05`'s guard remains the only formal check on an instruction, and it proves presence,
   not sufficiency. That gap is now accepted rather than open.
3. Langfuse's role narrows to tracing — and thereby *grows* in importance: with no evals,
   traces are the instrument empiricism actually runs on. Seeing what context reached the
   model and what came back is how `FR-05`'s claim gets checked in the wild rather than
   only in unit tests.

**Consequence:** written into `frame.md` Out of scope; Langfuse scoped to tracing only.

### 2026-09-11 — pure-tools: The constraint is aggregate mutation, not purity — ACCEPTED

Corrected by the user, and the correction is sharper than the version it replaces. Reading
a repository or calling a port is not the side effect that matters. The rule is: **the LLM
must not mutate aggregates.** It works on functions and abstractions built on the domain —
preferably part of it — so a tool like "find me all topics, using `foo`" is legitimate: it
performs a domain operation, calls a port, or invokes a domain service.

**Why the earlier framing was wrong.** The previous `pure-tools` entry (this date) argued
that vocabulary lookup violated `FR-06` because it needs `topics.candidates()` and
`EmbeddingPort.embed`, and concluded that candidates must therefore arrive through the
context so the tool could stay pure. That conclusion was built on a purity requirement that
is not the actual constraint, and it is withdrawn. `TopicRepository` and `TagRepository` are
**domain** ports already (`backend/src/domain/capture/ports.py`), so a lookup tool calling
them satisfies `FR-06` directly, with no context detour. `FR-05` stands on its own merits
and does not depend on that argument.
**Supersedes:** the purity analysis and the "two halves of one mechanism" claim in
`pure-tools` above.

**Consequence:** settled as `FR-07`.

### 2026-09-11 — draft-tool-call: The draft tool declares intent; it does not draft — ACCEPTED

`FR-07` collides with the first tool call the session accepted, and the collision resolves
cleanly.

**The collision.** Drafting mutates aggregates: `CaptureSession.draft_note` creates a
`Note` and sets `self.note_id` (`backend/src/domain/capture/capture_session.py:45-57`). If
no tool call may mutate an aggregate, then the draft tool cannot be the thing that drafts.

**The resolution, and the code already has its shape.** The tool call carries *intent* —
the user consented, here is the topic, the tags, the content — and the mutation happens
afterwards, in the application command, subject to the graph's legality check.
`GenerateReplyCommand.handle` is already built this way: the stream only sets `saw_draft`
and accumulates (`send_message.py:100-131`), and every aggregate mutation runs after the
loop closes, at `:137-161`, before `uow.commit()`. The model's signal and the aggregate
mutation are already separate concerns in this codebase. The tool call replaces the
chunk-shaped signal, not the mutation.

**Why this is better than what it replaces.** `_CONFIRMATION_PHRASES` matching produced the
same signal from six fixed strings; a tool call produces it from the model actually
understanding consent — which was the original argument for the tool — while `FR-07` keeps
the write where it already lives.

### 2026-09-11 — definition-of-done: Manual verification plus Langfuse observability — ACCEPTED

"Done" is capture and distill running end to end against a real provider, tested manually
by the author, and observable in Langfuse. Settled as `FR-08`.

**Why it follows from what is already settled.** With evaluation parked
(`evaluation-scope`), there is no automated quality gate and no BDD lane, so the author's
own use is the verification instrument and the trace is what makes that use legible. This
is coherent rather than a gap: `FR-05` guards context completeness in unit tests, and the
trace shows what actually reached the model in the wild.

**Consequence for `/roadmap`:** each slice ends with a manual check, not a green suite.
The roadmap should say so rather than implying an automated gate exists.
**Consequence:** Langfuse stops being optional. `FR-08` makes tracing part of done, which
means the deployment question blocks the effort rather than trailing it.

### 2026-09-11 — framework-portability: The domain must survive a framework swap — ACCEPTED

Stated as a project principle: `domain.shared` abstracts over *any* adapter built on an
LLM. Swapping pydantic-ai for LangChain means writing a new adapter while the domain
services, instructions, and graph stay put. Settled as `FR-09`.

**Why it needs a falsifier, and already has one.** A portability claim held with exactly
one adapter is untestable — the abstraction ends up shaped by the only library that ever
consumed it, and nobody finds out until the second one arrives. The usual answer is "build
two", which is not affordable here.

But this effort already produces a second consumer. Once the graph, instructions, and tool
definitions live in the domain, the deterministic in-memory adapters must drive off the
*same* domain artifacts — otherwise they cannot reproduce the behaviour the contract suites
check. That makes them a genuine non-pydantic-ai implementation of the abstraction, and any
pydantic-ai concept that leaks into the domain shows up immediately as something the
in-memory adapter cannot satisfy. InMemoryFirst
(`context/foundation/rules/layering.md`) turns out to be the portability test.

**Consequence:** the Out-of-scope boundary about in-memory adapters is sharpened — they do
not *reinvent* mode heuristics, but they do consume the same domain graph. Staying thin is
the outcome of the policy living elsewhere, not a licence to bypass it.

**Where portability will be hardest.** Streaming interleaved with tool calls is the most
framework-specific surface in reach: `ReplyGenerationPort.generate` yields
`AsyncIterator[ReplyChunk]` consumed by one `async for` (`send_message.py:100-131`), and
`research-pydantic-ai.md` already records that `run_stream` may stop at the first final
output with a non-text `output_type`. If `FR-09` breaks anywhere, it breaks there.

### 2026-09-11 — langfuse-deployment: Cloud vs self-host deferred to implementation — PARKED

The user defers the choice to the observability work itself, pending a cost calculation.

**Why PARKED rather than blocking.** `FR-08` requires model interactions to be visible as
Langfuse traces; it does not require a deployment mode, and the SDK surface is identical
either way — only credentials and `LANGFUSE_BASE_URL` differ (`research-langfuse.md`). So
nothing else in the frame depends on the answer.

**Consequence for `/roadmap` sequencing.** The cost calculation depends on span volume per
turn, and span volume depends on how many tool calls and graph steps a turn makes — which
is decided by the agent design slices, not by the observability slice. The observability
slice should therefore come after the agent shape is known, or the estimate is guesswork.

### 2026-09-11 — card-generation-split: One-shot vs per-card is plan-altitude — PARKED

The user places the choice at change-planning time. Correct by this document's own rule:
`frame.md` records what must be true when the effort is done, never what work to do, and
the shape of `CardGeneration` is a mechanism.

**Why the question was worth asking anyway.** It surfaced that the choice governs whether
`distill` participates in the tool-and-graph half of the domain module or only the
instruction half — a scope fact `/roadmap` needs even though the decision itself is
`/plan`'s. Recorded here so the slice that plans distill inherits the framing rather than
rediscovering it.

**Consequence:** three further threads are reclassified to the same altitude and parked
with it — where the `FR-05` guard runs and who assembles the instruction, which types
express a context requirement, and whether the graph holds a call budget. All are mechanism
under requirements already settled.

### 2026-09-11 — agent-handoff: Not adopted, not ruled out — PARKED

The user keeps the road open without deciding. Written into `frame.md` as a constraint on
the abstractions rather than as scope: nothing built here may make a later
agent-and-handoff concept impossible to add.

**Why the constraint needs a concrete reading.** "Do not preclude X" invites speculative
generality — the failure mode where an agent abstraction is introduced now, for a design
nobody has, and has to be dismantled before the real one can land. The reading recorded in
the body is the opposite: model phases and transitions, do not model agents at all. A graph
of phases accommodates a later handoff design; a premature `Agent` type obstructs it.

### 2026-09-11 — embedding-port-scope: `EmbeddingPort` stays in this effort — ACCEPTED

Decided by the user. It joins the four agent-shaped seams —
`TopicExtractionPort`, `ConfidenceAssessmentPort`, `ReplyGenerationPort`, `CardGeneration` —
so all five LLM-facing ports move together.

**Why it is worth recording despite being a one-word answer.** `EmbeddingPort` is the one
seam with no instruction, no tool call, and no graph position: the domain apparatus settled
by `FR-04`..`FR-07` has nothing to hold for it. Keeping it in the effort means the effort
contains one adapter that the effort's own central abstractions do not govern. That is a
deliberate asymmetry, not an oversight, and `/roadmap` should slice it accordingly rather
than forcing it through the same machinery.

### 2026-09-11 — adr-tool-call-exclusion: No ADR is owed — ACCEPTED

Decided by the user: this effort does not owe an architecture decision record.

**Where the unresolved text will surface, recorded so it is not a surprise.**
`context/adrs/capture-flow-domain-shape/decision.md` still reads "Tool-call mechanics the
agent runs while probing understanding (US-01) stay out of the domain model entirely", and
the same ADR fixes a `CaptureSession` shape carrying no conversational phase. Whoever runs
`/discover-contracts` or `/plan` on the capture slices will meet both. This frame's
Boundaries are the governing statement for this effort; the ADR text is narrower than it
appears, being about persistence of tool-call mechanics in the aggregate model rather than
about where policy lives.
