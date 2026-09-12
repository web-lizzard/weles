---
change_id: llm-adapter-domain-tools
title: The model reaches the domain only through tools that never mutate an aggregate
status: archived
created: 2026-09-12
updated: 2026-09-12
archived_at: 2026-09-12T21:34:50Z
effort_id: llm-adapter
slice_ref: S-04
---

## Notes

Closed without a plan. S-02 (`llm-adapter-capture-modes`) already delivered this
slice's outcome as a side effect: `domain/shared/graph/model.py`'s `Tool`/`ToolResult`
abstraction, per-state tool inventories (`Conversing.tools`, `Drafting.tools`), handlers
in `domain/capture/graph.py` that only read and compute (satisfying FR-07), and the
pydantic-ai rendering in `adapters/out/llm/capture/agent.py` (satisfying FR-06) were all
already in place.

The one real gap: `_event_from_tool_result` in `adapters/out/llm/capture/agent.py` had
no branch for `NoteContentProposal` — the `propose_note_content` tool's result was
silently dropped instead of producing `NoteContentProduced`, unlike the deterministic
adapter for the same port. Fixed in `54a4009`, along with round-trip test coverage for
every capture tool through the real adapter (previously only 2 of 7 were exercised
through `PydanticAiCaptureAgentAdapter`).
