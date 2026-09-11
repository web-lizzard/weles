---
status: closed
created: 2026-09-11
updated: 2026-09-11
---

## Boundaries

**In scope.**

The effort's thesis: the domain is the command centre over the LLM. Everything that
governs what the model does, and everything the model is allowed to reach back into, is
domain material.

LLM behaviour policy lives in the **domain** layer, not in application ports and not in
adapters. The domain owns *what the model is instructed to do*, expressed in the domain's
own vocabulary and without importing any model-provider library. Three kinds of thing sit
there, whatever they end up being called:

- **Transition graphs** — the legal phases of an agent-driven flow and the moves between
  them.
- **Instructions** — including the declaration of which context each one requires.
- **Tool-call configuration** — which capabilities a model may invoke, and under what
  constraints. The tools speak the domain's language and invoke domain functions.

The purpose of that placement is testability: this is the material that must be reachable
by ordinary unit tests, with no model in the loop. Maximizing that covered surface is the
reason the boundary sits where it does.

Adapters under `adapters/out/llm/` own *how* that policy is rendered and invoked: prompt
assembly, provider protocol, tool registration, structured-output decoding, streaming.

`domain/shared/` holds the abstractions; `domain/capture/` and `domain/distill/` hold the
concrete children.

A capture session's conversational mode — conversing, drafting a note, and the transitions
between them in both directions — is part of this effort.

`EmbeddingPort` is in scope for this effort, alongside the four agent-shaped seams.

Langfuse observability is in scope for this effort.

Handoff between agents is neither adopted nor ruled out. The domain abstractions must not
foreclose it: nothing in this effort may make a later agent-and-handoff concept impossible
to add. The cheapest way to honour that is to model phases and transitions, and not to
model agents at all yet — an agent concept introduced speculatively would have to be
removed before a real handoff design could land.

**Out of scope.**

This effort has no PRD: requirements are minted here as `FR-nn` rather than citing
acceptance criteria. It has no BDD/acceptance-test lane either; whatever proves the effort
done is established in this frame instead.

Reinventing conversational mode heuristics inside the deterministic in-memory adapters is
out of scope. Those adapters drive off the same domain graph and instructions as the LLM
adapters; they stay thin because the policy is not theirs to hold. If satisfying the
contract requires one of them to grow a mode machine of its own, the policy has been put in
the wrong layer.

Evaluation is out of scope. Judging whether an instruction produces *good* model output —
Langfuse datasets, scores, LLM-as-judge — is not part of this effort. The project is too
young and evaluation too expensive to carry before a working LLM prototype exists. Quality
is judged empirically, by using the thing. Evaluation becomes available as a later effort
once that prototype is the baseline it would measure against.

Consequently Langfuse enters this effort as **tracing only**.

## Requirements

- **FR-01** — The decision to move a capture session from conversation into note drafting
  rests with the user. The agent may encourage the transition; it never performs it
  unprompted, and no fixed phrase list stands in for the user's consent.
- **FR-02** — A capture session can return from note drafting to conversation, and can
  draft again afterwards. Neither direction is terminal while the session is open.
- **FR-03** — A session's assessed coverage is load-bearing: it influences what the agent
  says and when it encourages a transition, rather than being carried only as telemetry on
  the reply event.
- **FR-04** — The phases of an agent-driven flow and the legal moves between them are
  domain artifacts, exercisable by unit tests with no model and no adapter in the loop.
- **FR-05** — Every instruction declares the context required to carry out its task, and it
  is a deterministic invariant that an instruction is never dispatched with that context
  incomplete. The declaration is per-adapter-task and is enforced as a guard, not as a
  convention.
- **FR-06** — Tools exposed to the model are expressed in domain vocabulary and invoke
  domain functions, domain services, or domain ports — not adapter helpers. A tool's name,
  arguments, and result are readable as domain concepts.
- **FR-07** — No tool call mutates an aggregate. Tools read and compute; a model's request
  to change state arrives as a declared intent, and the aggregate mutation is performed by
  the application command, gated by the legal transitions of `FR-04`.
- **FR-08** — Capture and distill each run end to end against a real provider, verified by
  the author's own manual use, with every model interaction visible as a Langfuse trace.
- **FR-09** — The domain's LLM abstractions are framework-neutral. Replacing the adapter
  library — pydantic-ai for another — requires writing a new adapter and changing nothing
  under `domain/`: the services, instructions, tool definitions, and transition graph all
  stay as they are.
