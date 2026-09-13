---
change_id: llm-adapter-distill-live
title: Distill generates cards end to end against a real provider
status: implementing
created: 2026-09-12
updated: 2026-09-13
archived_at: null
effort_id: llm-adapter
slice_ref: S-06
---

## Notes

<!-- Materialized from effort `llm-adapter`, slice S-06. Run /plan llm-adapter-distill-live to write the plan. -->

**Materialized ahead of schedule, by explicit request.** S-06's roadmap prerequisite
S-03 (`llm-adapter-instruction-context`) was still `in_progress` (phase 7 of its
`todos.md`) at materialization time — the normal `/roadmap` gate would have refused
this. Done anyway to capture design intent from this session before it was lost;
`/plan` on this change should re-check that S-03 has actually reached `done` before
committing to phase order, since S-06 is meant to build on the shared instruction
abstractions S-03 lands.

**Design intent carried over from this session's discussion, not yet a decision:**
The real LLM will produce some damaged/weak card proposals. Rather than relying only
on the deterministic anchor-grounding check already in
`application/distill/commands/generate_cards.py` (`NoteDocument.locate`), the user
wants a second LLM pass that reviews the first pass's output before cards are
persisted — a review/critique step, not just structural validation.

Leaning **against** a `Graph`/`StateMachine` (domain/shared/graph) for this: unlike
capture's phase, generate → review has no reason to persist across separate requests
or user turns — it can run as two sequential model calls inside one
`GenerateCardsCommand.handle()`, each using the existing `Instruction`/`Tool`
abstractions from `domain/shared/instruction` and `domain/shared/graph/model`
directly, without `State`/`Transition`/`Graph`. A graph would only be justified if
review needed to loop back to generation across separate persisted steps rather than
within one command invocation. This should be revisited and settled explicitly during
`/plan`, not assumed.
