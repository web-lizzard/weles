---
status: closed
created: 2026-09-12
updated: 2026-09-12
---

## Boundaries

**In scope.**

Instructions for a flow's model-facing tasks are domain artifacts. What the model is told
to do is authored in the domain's own vocabulary, with no model-provider library imported,
and is exercisable by ordinary unit tests with no model and no adapter in the loop.

An instruction belongs to a phase of a flow's graph, not to the flow as a whole. Each phase
wants the model to behave differently, and different prose per phase is how that is forced —
so the phase is what authors it. The instruction is built at runtime from the turn's context
and handed to the adapter, which renders and dispatches it and holds none of its text.

The instruction is not assembled from context blindly. **An instruction is an ordered
sequence of named blocks**, each block a piece of prose the phase authors. A block is
required or optional: the required set is the declaration FR-05 asks for, and an instruction
with a required block missing cannot be constructed. Whether an optional block is present is
the phase's decision, taken from the context of that turn.

Conditionality therefore lives in the domain, not in the model's reading. A block the phase
withholds is never rendered and so can never be acted on — the same rule S-02 settled for
tools. This is what makes assessed coverage load-bearing under FR-03: high coverage adds the
block that lets the agent say it is ready to draft, and at low coverage the model never sees
that as an option at all.

**Building an instruction is synchronous and reaches no port.** The phase reads the context
the machine already carries and nothing else. An instruction describes the turn as it stands
now, and fetching to enrich it would buy staleness with latency.

Blocks are what the domain hands across the port. Turning them into whatever instruction
payload a provider takes is the adapter's work, as tool rendering is — so a library that
wants one string and a library that wants a sequence of system messages are both served
without the domain changing, which is FR-09.

**The deterministic capture adapter is one of the adapters that render an instruction, not
an exception to the rule.** It receives the same blocks the provider-backed adapter does and
speaks from them, so the prose it emits is authored in the domain rather than held as
constants of its own. Where it once had a line to say, it now says the block's.

What stays with it is how a fake agent fakes being one: how text is chunked and paced, and
how it simulates a judgement the real agent gets from a model. The instruction carries what
the domain tells an agent; it does not carry a double's impersonation mechanics.

Recognising consent is one such simulated judgement, and the double recognises it by a fixed
list of phrases, because no deterministic adapter can be ready for arbitrary prose. **That
list is an impersonation mechanic and is not domain policy**: it stays in the adapter, never
becomes a block, and FR-01's prohibition on a fixed phrase list continues to bind the
product's agent, which reads consent with a model. It follows that the deterministic path's
consent recognition is not evidence that FR-01 is satisfied — it exists so that path can reach
note drafting at all. FR-01 is demonstrated on the provider-backed path, under FR-08.

Nothing in the adapter infers the phase for itself. The instruction it is handed is already
the current phase's, so an adapter reading the offered tool set to work out which phase it is
in is redundant, and is the mode machine of its own that the effort forbids.

`domain/shared/` holds the abstraction — the instruction type and the protocol for building
one — and knows nothing of any flow. `domain/capture/` and `domain/distill/` hold the prose
and the concrete builders. This follows the effort frame's placement rule and the shape
`domain/shared/graph/` already uses. **This change reaches `domain/shared/` and
`domain/capture/` only**; the placement rule stays true for distill whenever distill arrives.

**The builder is a domain abstraction, not a port and not an adapter.** It is a declared
protocol for constructing an instruction, and the completeness guard of FR-05 lives in its
construction logic rather than beside it. Each phase's builder is unit-tested on its own.

**An instruction cannot be constructed from outside its builder.** The type is closed, so
the single construction path is a property of the type rather than of the current
composition, and FR-05's guard cannot be stepped around by a caller who declines to use the
builder. Bypassing is not merely discouraged; it is unavailable.

**The phase holds its builder and builds per call**, exactly as it already decides which
tools to offer. The machine asks the current phase for the instruction, reading the context
it already carries in memory, and the application hands the result across the port with the
tools. The machine is still never given a model-facing port and still consumes no stream.

A session's assessed coverage reaches the domain and survives the turn. It is returned by
the model as a tool result, applied to the machine as an event, and persisted on the session,
so that a later turn's instruction can be built from it. Without that it cannot be
load-bearing on what the agent says, which FR-03 requires.

The session keeps every assessment, as a collection on `CaptureSession` beside the phase. The
aggregate stays the single durable carrier of session state. Overwriting is not enough: a
discarded assessment cannot be recovered later, while a kept one can always be ignored.

**How coverage moved is a domain judgement, not the model's.** The direction of the trend is
computed deterministically while the instruction is built, and what crosses the port is a word
for it, never the number. A coverage that is climbing changes the agent's tone towards
encouraging the session to close; a coverage that is flat and low affirms keeping it open.
That judgement is exercisable by a unit test with no model in the loop, which is the whole
point of placing it here.

The number travels inward only. The model supplies an assessment through a tool and never
reads one back, so no turn depends on the model's own reading of a float it emitted earlier.
The float remains available as telemetry on the reply event, which is a different reader.

Whether a capture session is better modelled as a stream of events with the aggregate derived
from it is an open question of the author's, neither adopted nor ruled out here. Nothing in
this change may make that reshaping harder than it already is: coverage is written through the
machine as an applied event, exactly as the phase is, so both arrive by the same route a later
event-sourced reading would already use.

**Out of scope.**

Judging whether an instruction produces *good* model output. Evaluation — Langfuse datasets,
scores, LLM-as-judge — is out of scope for the whole effort; quality is judged empirically
by use.

Rendering a phase's declared tools as provider-facing tool definitions — slice S-04
(FR-06, FR-07).

Distill's instructions. Distill has no agent port, no phase graph, and no live adapter until
S-06; authoring its prose against an abstraction no distill code yet consumes would be
speculative. The abstraction is therefore shaped by capture alone, and that is the risk this
change accepts.

## Requirements

- Cites **FR-05** (`context/efforts/llm-adapter/frame.md`) — every instruction declares the
  context required to carry out its task, and it is a deterministic invariant that an
  instruction is never dispatched with that context incomplete. The declaration is
  per-adapter-task and is enforced as a guard, not as a convention.
- Cites **FR-03** — assessed coverage is load-bearing on what the agent says and when it
  encourages a move, rather than being carried only as telemetry on the reply event.
- Cites **FR-09** — the domain's LLM abstractions are framework-neutral: the instruction
  type, the builder protocol, and the prose stay unchanged when the adapter library is
  replaced.
