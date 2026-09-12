# Capture Capture-Mode Graph and the Pydantic AI Agent Adapter — Plan Brief

> Full plan: `plan.md` · Revision 4 (2026-09-12); prior versions in `plan-versions/v1-*`…`v3-*`

## What & Why

Slice S-02 makes the `llm-adapter` thesis falsifiable: a capture session's phases and the legal moves
between them become domain artifacts, reached by the model only through tools. This plan fills the
bodiless declarations `/discover-contracts` left, completes the consent model, rewrites the command
onto one port, builds the Pydantic AI adapter first, and gives actions the dependencies they need.

## Starting Point

Mechanics, capture composition, `CaptureAgentPort` and `MessageRepository.history` declared but
bodiless; the tree is knowingly red. The command holds three model-facing ports and decides drafting
from a phrase list.

## Desired End State

A phase changes only by crossing a guarded edge: the model signals consent through a tool, an action
persists it, the guard reads it; leaving drafting is symmetric. `GenerateReplyCommand` holds one port
and maps events to DTOs without reaching a repository — every write staged by an action, committed by
the command.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Pydantic AI reach | `TestModel` / `FunctionModel` only | Proves FR-09 and the whole seam while leaving keys, cost and live cadence to S-05. | Plan |
| Superseded ports | Removed in this change | One route to a model instead of two; the shaping log names this reach explicitly. | Plan |
| Consent carrier | Tool result → `apply` → value object on the session | Consent is the model's reading, so it cannot exist before the model runs. | Plan |
| Who chooses the move | Machine reports available transitions, command decides | Keeps the choice where the use case lives, and leaves room for the model to choose later. | Plan |
| Transition timing | At the start of each segment, at most two segments | Drafts land in the turn consent was given, and a carried intent is spent before the model sees the wrong tools. | Plan |
| Return edge | Guarded on a recognised request | Without it every drafting turn burns a segment returning to a conversation nobody asked for. | Plan |
| Loop termination | Each edge consumes the intent that permitted it | An intent is single-use, so nothing permits a further move until the model produces a new one. | Plan |
| Transition weights | Not modelled | Disjoint guards already express precedence, and a weight would need a legend a description gives for free. | Plan |
| Mid-turn failure | Roll the whole turn back | `UnitOfWork` already gives it, and a retry stays clean. | Plan |
| Deterministic stand-in | Keeps `"that's all"`, emits a tool result | Acceptance scenarios in capture-flow *and* distill-flow depend on the phrase. | Plan |
| Tool-name invariant | `model_validator` on `Tool` | A misnamed tool fails at import rather than mid-conversation. | Plan |
| Tracing | `langfuse.session.id` per turn | One capture session reads as one bucket rather than scattered spans. | Plan |
| Message recording | Command-raised events through `apply` | Keeps `apply` the only way the context changes, and the split union stops an adapter raising them. | Plan |
| Action dependencies | Fourth type parameter, actions only | Guards read persisted state and tools compute over the context; only actions have something to fetch. | Plan |
| Commit boundary | `CaptureDeps` exposes domain repositories, never the `UnitOfWork` | No domain port has a commit method, so an action cannot reach the boundary — held by the type, not a convention. | Plan |
| Draft materialisation | `NoteDraft` on the turn, realised on `DraftCompleted` | `NoteContent` rejects empty and `Note.draft` demands content, so no note can exist when a topic is proposed. | Plan |

## Scope

**In scope:** mechanics bodies and the tool-name validator; transition reporting; the consent and
return model; both adapters; `MessageRepository.history`; the command rewrite; removal of the three
superseded ports and `ReplyChunk`; action dependencies, and vocabulary resolution and note
construction moving into the domain.
**Out of scope:** a real provider call (S-05); tool rendering (S-04); instructions (S-03);
dependencies for tools; renaming repository `add` to `save`; a third note-shaping phase.

## Architecture / Approach

Bottom-up, since each layer's tests need the one below: mechanics → composition → adapters → command
→ removal → dependencies. Stubs phases (2, 4, 6, 8, 10, 15) appear only where a test would otherwise
fail to collect on a new symbol imported by name.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Graph mechanics bodies | Executable mechanics plus the tool-name validator | Validator needs pydantic introspection in the domain |
| 2. Edge vocabulary (stubs) | Edge aliases, `State.description`, new machine surface | Supersedes the shaping session's `guard-concept` decision |
| 3. State machine behaviour | `available_transitions`, `transition`, `current_state_name` | The machine must report, never choose |
| 4. Consent symbols (stubs) | Value object, tools, results, events | `TurnOpened` removal touches the event union |
| 5. Capture graph behaviour | Guards, actions, per-turn tool filtering | Consent guard must read persisted state, not the event |
| 6. Message events (stubs) | `AgentEvent` split, two command-raised events | Narrows the port signature set in discover-contracts |
| 7. Messages reach the machine | A turn's own exchange enters the context | Fixes consent on a first-message turn and drafting from a stale transcript |
| 8. Pydantic AI adapter (stubs) | Adapter skeleton, session id on tracing | Tracing change is shared with the embedding adapter |
| 9. Pydantic AI stream mapping | `run_stream_events` → `CaptureEvent`, traced | Library event surface is the least familiar ground here |
| 10. In-memory adapter (stubs) | Stand-in skeleton | — |
| 11. Stand-in behaviour + history | Acceptance scenarios keep running; port satisfied again | Losing `"that's all"` would break distill-flow too |
| 12. Command rewrite | One port, the turn loop, rollback posture | The loop must terminate; 827 lines of tests rewritten |
| 13. Remove superseded ports | One route to a model; composition rewired | Widest blast radius — compose, integration, BDD |
| 14. Dependencies reach actions | `DepsT` across the mechanics, forwarded by the machine | Touches every generic signature in `shared/graph` at once |
| 15. Domain vocabulary + deps (stubs) | `CaptureDeps`, `NoteDraft`, `DraftCompleted`, resolver moved | Relocation must stay behaviour-free to be verifiable |
| 16. Drafting actions build the note | `Drafting` gains actions; the ordering invariant moves in | Redraft path must match `_apply_redraft` exactly |
| 17. Command stops resolving | Pure mapping, deps assembly, one commit | `DraftDoneEvent` now reads the turn, not buffers |

**Prerequisites:** none beyond the closed `frame.md` and `discover-contracts.md`; S-01 landed the
`adapters/out/llm/` package and tracing. **Estimated effort:** large — seventeen phases, ten test-driven.

## Open Risks & Assumptions

- The loop terminates because each edge consumes its intent; the two-segment cap states what this use case needs rather than guarding a runaway.
- Guards are assumed disjoint; two available at once is a defect only the mechanics suite catches.
- Pydantic AI's event surface is assumed stable at 2.35.3, verified against the installed package.
- Phase 11's blast radius reaches distill-flow, whose scenarios depend on capture's stand-in.
- Phases 14–17 append after 13 per the revision protocol, so they start from a green tree.

## Success Criteria (Summary)

- A phase changes only through a guarded edge, and consent recognised in a turn drafts a note in it.
- `uv run pytest` green across unit, contract, integration and BDD suites, nothing skipped.
- No superseded port, no `ReplyChunk`, and no repository call or draft bookkeeping in `send_message.py`.
