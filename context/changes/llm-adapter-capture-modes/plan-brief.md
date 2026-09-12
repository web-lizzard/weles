# Capture Capture-Mode Graph and the Pydantic AI Agent Adapter — Plan Brief

> Full plan: `plan.md`

## What & Why

Slice S-02 makes the `llm-adapter` effort's thesis falsifiable: a capture session's phases and the
legal moves between them become domain artifacts, reached by the model only through tools.
`/discover-contracts` left the mechanics and the graph on disk as bodiless declarations; this plan
fills them, completes the consent model, rewrites the command onto one port, and builds the Pydantic
AI adapter ahead of the in-memory one.

## Starting Point

The mechanics, the capture composition, `CaptureAgentPort` and `MessageRepository.history` are
declared but bodiless, and the tree is knowingly red — `InMemoryMessageRepository` no longer satisfies
its port. The command still holds three model-facing ports and decides drafting from a phrase list.

## Desired End State

A session's phase changes only by crossing a guarded edge. The model signals consent through a tool,
an action persists it on the session, and the guard reads that persisted value; leaving drafting is
symmetric. `GenerateReplyCommand` holds one port and loops while a move is available.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Pydantic AI reach | `TestModel` / `FunctionModel` only | Proves FR-09 and the whole seam while leaving keys, cost and live cadence to S-05. | Plan |
| Superseded ports | Removed in this change | One route to a model instead of two; the shaping log names this reach explicitly. | Plan |
| Consent carrier | Tool result → `apply` → value object on the session | Consent is the model's reading, so it cannot exist before the model runs; the session is the only carrier that survives a turn. | Plan |
| Transition timing | `while` on a machine predicate, one stream segment per phase | Notes are drafted in the same turn consent was given, and a third phase would need no command change. | Plan |
| Return edge | Guarded on a recognised request | An unguarded return oscillates forever inside the loop; a satisfiable guard still honours FR-02. | Plan |
| Mid-turn failure | Roll the whole turn back | `UnitOfWork` already gives it, and a retry stays clean. | Plan |
| Deterministic stand-in | Keeps `"that's all"`, emits a tool result | Acceptance scenarios in capture-flow *and* distill-flow depend on the phrase; the adapter still decides no phase. | Plan |
| Tool-name invariant | `model_validator` on `Tool` | A misnamed tool fails at import rather than mid-conversation. | Plan |
| Tracing | `langfuse.session.id` per turn | One capture session reads as one bucket rather than scattered spans. | Plan |

## Scope

**In scope:** mechanics bodies and the tool-name validator; the machine plus a target-free transition
predicate; the consent and return model; both adapters; `MessageRepository.history`; the command
rewrite; removal of the three superseded ports and `ReplyChunk`.

**Out of scope:** a real provider call (S-05); provider-facing tool rendering (S-04); instructions
(S-03); renaming repository `add` to `save`; a third note-shaping phase; routing between tools.

## Architecture / Approach

Bottom-up, since each layer's tests need the one below: mechanics → capture composition → adapters →
command → removal. Stubs phases appear only where a test would otherwise fail to collect — phases 3, 5
and 7 introduce new classes; the rest add methods to classes that already exist.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Graph mechanics bodies | Executable mechanics plus the tool-name validator | Validator needs pydantic introspection in the domain |
| 2. State machine bodies | `apply`, `transition`, and the `can_advance`/`advance` pair | A leaky predicate would put phase names in the command |
| 3. Consent symbols (stubs) | Value object, tools, results, events | `TurnOpened` removal touches the event union |
| 4. Capture graph behaviour | Guards, actions, per-turn tool filtering | Consent guard must read persisted state, not the event |
| 5. Pydantic AI adapter (stubs) | Adapter skeleton, session id on tracing | Tracing change is shared with the embedding adapter |
| 6. Pydantic AI stream mapping | `run_stream_events` → `CaptureEvent`, traced | Library event surface is the least familiar ground here |
| 7. In-memory adapter (stubs) | Stand-in skeleton | — |
| 8. Stand-in behaviour + history | Acceptance scenarios keep running; port satisfied again | Losing `"that's all"` would break distill-flow too |
| 9. Command rewrite | One port, the turn loop, rollback posture | The loop must terminate; 827 lines of tests rewritten |
| 10. Remove superseded ports | One route to a model; composition rewired | Widest blast radius — compose, integration, BDD |

**Prerequisites:** none beyond the closed `frame.md` and `discover-contracts.md`; S-01 landed the
`adapters/out/llm/` package and tracing. **Estimated effort:** large — ten phases, six test-driven.

## Open Risks & Assumptions

- The loop terminates because the return edge is guarded; the iteration cap is a safety net, not the
  mechanism. Relaxing that guard regresses it to oscillation.
- Pydantic AI's event surface is assumed stable at 2.35.3 — `run_stream_events` with per-call
  `toolsets` was verified against the installed package, not just the docs.
- Phase 10's blast radius reaches distill-flow, whose scenarios depend on capture's stand-in.

## Success Criteria (Summary)

- A phase changes only through a guarded edge, and consent recognised in a turn drafts a note in it.
- `uv run pytest` green across unit, contract, integration and BDD suites, nothing skipped.
- No `ReplyGenerationPort`, `TopicExtractionPort`, `ConfidenceAssessmentPort` or `ReplyChunk` remains.
