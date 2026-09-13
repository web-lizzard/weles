---
change_id: graph-task-tier-hint
title: Task-tier hint on graph states for model selection
status: new
created: 2026-09-13
updated: 2026-09-13
archived_at: null
origin: llm-adapter-distill-live
---

## Notes

Give a graph state (`domain/shared/graph/`) a way to hint how much reasoning
power its task needs — not a concrete model name, but something like a
task-tier/complexity level a structured-task adapter can map through a
task-type × tier → model matrix, so different phases (e.g. distill's review
vs. merge) can ask for different model capability without the domain ever
naming a provider model.

Emerged from a conversation about `context/foundation/rules/graph-state-machines.md`
and its parallel idea, "let the model pick the next transition from
`State.description`" (deferred separately — see the `project_graph_routing_heuristic`
memory).

Naming note: don't call this "effort" — that word already names the roadmap
effort container (`context/efforts/`) and would collide with that vocabulary
throughout `/roadmap`, `/prd`, etc. Consider `TaskTier`, `ReasoningLevel`, or
similar instead.

Open design question to settle during framing/planning: is this a static
per-state declaration (like `StructuredState.output`), or something computed
per-context (like `output_without_model`) — e.g. a regenerating phase might
want a different tier than the first pass over the same content.
