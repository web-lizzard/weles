# Capture Capture-Mode Graph and the Pydantic AI Agent Adapter — Implementation Plan

## Overview

Slice S-02 of the `llm-adapter` effort makes the effort's thesis falsifiable: the phases of a
capture session and the legal moves between them become domain artifacts, and the model reaches
them only through tools. `/discover-contracts` already put the mechanics and the capture graph on
disk as declarations with empty bodies. This plan fills those bodies, completes the consent model
in the shape the planning session settled, rewrites `GenerateReplyCommand` onto a single
`CaptureAgentPort`, and builds two adapters behind that port — the Pydantic AI one first.

The working tree is knowingly red at the start: `InMemoryMessageRepository` no longer satisfies
`MessageRepository`, and its contract suite is skipped. Phase 8 closes that.

## Current State Analysis

**What the contract-shaping session left on disk.** `domain/shared/graph/model.py` declares
`Condition`, `Action`, `ToolResult`, `ToolArguments`, `ToolHandler`, `Tool`, `State`, `Transition`
and `Graph`; `domain/shared/graph/machine.py` declares the `StateMachine` ABC. Every method body
is `...`, and both modules carry blocking `# ruff: noqa: B027` / `# pyright: reportUnusedParameter=false`
comments that exist only while the bodies are absent. `domain/capture/graph.py` declares
`CaptureMachine`, `Conversing`, `Drafting`, five tools with their results, `consent_given` and
`_CAPTURE_GRAPH`. `domain/capture/turn.py` declares `CaptureTurn` and the `CaptureEvent` union.
`domain/capture/ports.py` declares `CaptureAgentPort` and `MessageRepository.history`.

**What the session did not cover**, verified by grep across `src` and `tests` — zero hits on each:
the consent value object, the consent and return-to-conversation tools and their events, the guard
on the return edge, the transition predicate the command's loop needs, and both adapters behind
`CaptureAgentPort`. The session shaped the mechanics and the graph; the consent model as settled in
planning, and everything adapter-side, is this plan's.

**What the consent model looked like before planning, and why it changes.**
`turn.py:39` carries `TurnOpened.consent_signalled: bool` — a flag the command was to supply before
calling the adapter. Nothing can fill it: consent is the model's reading, so it does not exist until
the model has run. Consent instead becomes a tool result that flows through `apply`, and an action
persists it as a value object on `CaptureSession`, which is the only carrier that survives between
turns. `TurnOpened` does not survive in its current shape.

**What the command does today.** `GenerateReplyCommand` (`application/capture/commands/send_message.py`)
holds three model-facing ports — `TopicExtractionPort`, `ConfidenceAssessmentPort`,
`ReplyGenerationPort` — and carries the mode decision itself: `session.topic is None` at line 83
gates topic extraction, and `_should_draft` in the in-memory adapter (`reply_generation.py:74`)
decides drafting from a frozen phrase list. Both are policy in the wrong layer; the graph takes them.

**What the acceptance layer assumes.** `"that's all"` is written into `tests/features/capture-flow/`
US-04, US-06, US-07 **and** `tests/features/distill-flow/` US-02, US-03. The deterministic stand-in
must keep reacting to it or distill-flow breaks — a flow outside this change.

### Key Discoveries:

- `backend/src/domain/capture/graph.py:207` — the `DRAFTING -> CONVERSING` edge is deliberately
  unguarded, justified in-file as the cheapest guarantee that FR-02's "never terminal" holds. In a
  `while` loop that becomes an infinite oscillation: the move back is always available, so the loop
  would ping-pong without ever reaching the stream. The edge gains a guard.
- `backend/src/domain/shared/graph/machine.py:56` — `can_transition(target, event)` requires a named
  target. A command using it would have to name `CapturePhase.DRAFTING`, contradicting `frame.md`'s
  rule that adding a phase or edge changes no command. The machine needs a target-free predicate.
- `pydantic_ai` 2.35.3 exposes `Agent.run_stream_events()`, yielding `PartStartEvent`,
  `PartDeltaEvent`, `ToolCallEvent` and `ToolResultEvent` on one stream — text and tool activity
  together, which is exactly what mapping to `CaptureEvent` needs.
- `Agent.run_stream_events(..., toolsets=...)` accepts toolsets per call, and
  `FunctionToolset(tools=[...])` is constructible per turn — so a phase's filtered tool set can be
  handed over per invocation rather than bound to the agent at construction.
- `backend/src/adapters/out/llm/capture/embedding.py` plus `adapters/out/llm/tracing.py` are the
  established shape for an LLM adapter here: wrap the call in `observation(...)`, record model,
  output and usage. `tracing.py` sets `langfuse.observation.*` attributes and has no session concept.
- `backend/src/adapters/compose.py:143` — `_build_embedding_port` branches on a settings enum to pick
  deterministic vs real adapter. The capture agent follows that precedent.
- `backend/tests/unit/capture/contracts/test_message_repository_contract.py:11` — `pytestmark` skips
  the whole module pending `InMemoryMessageRepository.history`.

## Desired End State

A capture session's phase lives on `CaptureSession` and changes only by crossing a declared edge
whose guard passed. The model signals consent by calling a tool; an action persists it; the guard
reads the persisted value object. Leaving note drafting is symmetric — the user asks, the model
recognises, a tool reports it. `GenerateReplyCommand` holds one `CaptureAgentPort` and loops while
the machine says a move is available, closing each stream segment before opening the next against
the new phase's tools. Two adapters satisfy that port: a Pydantic AI one, proven with `TestModel`
and `FunctionModel`, and a deterministic in-memory one. The three old model-facing ports and the
`ReplyChunk` union are gone.

Verified by: `uv run pytest` green across unit, contract, integration and BDD suites; `uv run ruff
check src tests` clean; `uv run basedpyright src tests` at zero errors — including the contract
module whose `pytestmark` is removed.

## What We're NOT Doing

- **Calling a real provider.** The Pydantic AI adapter is exercised only through `TestModel` and
  `FunctionModel`. Keys, live cadence and cost stay with S-05 (`llm-adapter-capture-live`).
- **Rendering tools as provider-facing definitions** beyond what `FunctionToolset` needs to run the
  adapter's own tests — the declaration-to-schema story is S-04 (FR-06, FR-07).
- **Instructions and their context declarations** — S-03 (FR-05).
- **Renaming repository `add` to `save`.** The rule holds, but `add` sits on five capture ports at
  once and rewriting them is a separate refactor across the layer. Explicitly deferred by the user.
- **A third "shaping the note" phase**, per `frame.md`.
- **Routing or selecting between a phase's tools** — the graph offers a set; nothing chooses within it.
- **Mode heuristics in adapters.** The deterministic stand-in may recognise a phrase, but only to
  emit a tool result; it never decides a phase.

## Implementation Approach

Bottom-up, because each layer's tests need the one below to exist. Mechanics first (phases 1–2),
then the capture composition's consent and return model (3–4), then the adapters behind the already
declared port (5–8) with Pydantic AI ahead of the in-memory one at the user's direction, then the
command that consumes all of it (9), then removal of what the new seam replaces (10).

Stubs phases appear only where a test would otherwise fail to collect. Phases 1, 2, 8 and 9 add
methods to classes and modules that already exist — a test importing them collects and fails on
behaviour, which is the red half doing its job. Phases 3, 5 and 7 introduce new classes and modules,
so each is preceded by its own stubs phase.

## Critical Implementation Details

The `while` loop and the unguarded return edge are incompatible: once in `DRAFTING`, the move back is
permanently available, so a loop conditioned on "a move is possible" never terminates. Guarding the
return edge on a recognised request is what makes the loop finite, and it is also what FR-02 asks for
— the condition is satisfiable in any turn, so drafting never becomes terminal. A bounded iteration
count backs this up as a safety net, not as the primary mechanism.

Breaking out of `async for` mid-stream leaves Pydantic AI's run context open; every segment is wrapped
in `contextlib.aclosing` so an early exit at a transition disposes the run properly.

## Phase 1: Graph mechanics bodies and the tool-name invariant

### Overview

Fill every method body in `domain/shared/graph/model.py` and add the validator that ties a tool's name
to its result's discriminator. Proven against a throwaway graph that is not capture's, so reusability
is a tested claim rather than an assertion (`frame.md`).

### Changes Required:

#### 1. Graph mechanics

**File**: `backend/src/domain/shared/graph/model.py`

**Intent**: Make the declared mechanics executable, and make a misnamed tool unconstructible rather
than a mystery at conversation time.

**Contract**: `State.get_tools(context)` and `State.get_actions(context, event)` return the full
inventory by default. `Graph.outgoing(source)` returns the edges leaving a state by target, empty
mapping when none. `Graph.is_terminal(name)` reports no outgoing edge. `Graph.terminal_states`
returns the frozenset of such states. `Graph.reachable_from(source)` returns every state reachable by
one or more edges, guards not evaluated. A new `model_validator` on `Tool` asserts the declared
`result` type's `tool` field default equals `name`, raising `ValueError` otherwise. Remove both
blocking comments at the top of the file once bodies land.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/shared/test_graph_model.py -v` passes
- `cd backend && uv run ruff check src/domain/shared/graph` reports no `B027` suppression left in place
- `cd backend && uv run basedpyright src/domain/shared/graph` reports zero errors

---

## Phase 2: State machine bodies and the transition predicate

### Overview

Fill `StateMachine`'s bodies and add the target-free predicate and mover the command's loop needs, so
the graph's inventory never leaks into the application layer.

### Changes Required:

#### 1. State machine

**File**: `backend/src/domain/shared/graph/machine.py`

**Intent**: Give the mechanics a way to answer "is any move available for this event?" and "take it",
without the caller naming a phase.

**Contract**: `__init__(context)` stores the context. `context` and `current_state` expose it and the
resolved `State`. `get_tools()` delegates to the current state. `apply(event)` runs the actions the
current state warrants for that event and crosses no edge. `can_transition(target, event)` reports
whether that edge exists and its guard passes. `transition(target, event)` runs the edge's actions
then writes the new name via `enter_state`, returning whether the move happened. Two new methods:
`can_advance(event) -> bool`, true when any outgoing edge's guard passes for this event, and
`async advance(event) -> bool`, which takes the first such edge and reports whether it moved. Remove
both blocking comments.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/shared/test_graph_machine.py -v` passes
- `cd backend && uv run basedpyright src/domain/shared/graph` reports zero errors

---

## Phase 3: Consent and return-to-conversation symbols (stubs)

### Overview

Materialize the symbols phase 4's tests import. No behaviour — declarations and empty bodies only.

### Changes Required:

#### 1. Consent value object on the session

**File**: `backend/src/domain/capture/value_objects.py`, `backend/src/domain/capture/capture_session.py`

**Intent**: Give the session a durable carrier for the user's expressed wish to draft, so it survives
between turns the way the phase itself does.

**Contract**: `DraftingConsent(BaseModel, frozen=True)` in `value_objects.py`.
`CaptureSession.drafting_consent: DraftingConsent | None = None`, plus
`record_drafting_consent(self, consent: DraftingConsent) -> None` with an empty body.

#### 2. Tools, results and events

**File**: `backend/src/domain/capture/graph.py`, `backend/src/domain/capture/turn.py`

**Intent**: Declare the two recognitions — consent to draft, and the request to return to
conversation — as tools with results and matching domain events.

**Contract**: In `graph.py`: `DraftingConsentSignal(ToolResult, frozen=True)` pinning
`tool: Literal["signal_drafting_consent"]`; `ConversationRequest(ToolResult, frozen=True)` pinning
`tool: Literal["request_conversation"]`; handlers `_signal_drafting_consent` and
`_request_conversation`; module-level `_SIGNAL_DRAFTING_CONSENT` and `_REQUEST_CONVERSATION` tools;
action `_record_drafting_consent`; guard `conversation_requested`. In `turn.py`:
`DraftingConsentSignalled` and `ConversationRequested` event models, both added to the `CaptureEvent`
union; `TurnOpened` is removed along with its `consent_signalled` field.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run python -c "import domain.capture.graph, domain.capture.turn"` succeeds
- `cd backend && uv run basedpyright src/domain/capture` reports zero errors

---

## Phase 4: Capture graph behaviour — guards, actions and tool filtering

### Overview

Make capture's composition decide things: when consent counts, when a return is permitted, which
tools a phase offers this turn, and what an event makes happen.

### Changes Required:

#### 1. Guards and the consent action

**File**: `backend/src/domain/capture/graph.py`, `backend/src/domain/capture/capture_session.py`

**Intent**: Move the drafting decision out of the adapter's phrase list and the topic decision off the
command, into the graph where `frame.md` puts them.

**Contract**: `consent_given(context, event)` returns true when `context.session.drafting_consent` is
set and `context.messages` is non-empty — it reads persisted state, not the event's payload.
`_record_drafting_consent(context, event)` persists the consent in memory only when
`context.messages` is non-empty, which is the invariant that keeps a consent without a conversation
from being recorded. `conversation_requested(context, event)` returns true when the event is a
`ConversationRequested`. `CaptureSession.record_drafting_consent` assigns the value object.

#### 2. Phase inventories and filtering

**File**: `backend/src/domain/capture/graph.py`

**Intent**: Let each phase narrow its own tool set per turn, and run only the actions an event warrants.

**Contract**: `Conversing.tools` gains `_SIGNAL_DRAFTING_CONSENT`; `Conversing.get_tools` withholds
`_PROPOSE_SESSION_TOPIC` once `context.session.topic` is set — the filter `send_message.py:83`
performs today. `Conversing.get_actions` returns `_assign_session_topic` only for a
`SessionTopicProposed` and `_record_drafting_consent` only for a `DraftingConsentSignalled`.
`Drafting.tools` gains `_REQUEST_CONVERSATION`. `_assign_session_topic` puts the proposed topic on the
session. The `DRAFTING -> CONVERSING` transition gains `guard=conversation_requested`, and the
in-file comment justifying its absence is replaced with one explaining why the guard is required.
The five proposal handlers return their results from the arguments the model sent.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/test_capture_graph.py -v` passes
- `cd backend && uv run pytest tests/unit/capture/test_model.py -v` passes
- `cd backend && uv run basedpyright src/domain` reports zero errors

---

## Phase 5: Pydantic AI capture agent adapter (stubs)

### Overview

Materialize the adapter module and class phase 6's tests import.

### Changes Required:

#### 1. Adapter skeleton

**File**: `backend/src/adapters/out/llm/capture/agent.py`

**Intent**: Declare the Pydantic AI implementation of `CaptureAgentPort` before giving it behaviour.

**Contract**: `PydanticAiCaptureAgentAdapter` taking a configured `pydantic_ai.Agent` and a model name
at construction, exposing
`def converse(self, turn: CaptureTurn, tools: Sequence[Tool[CaptureTurn, ToolResult]]) -> AsyncIterator[CaptureEvent]`
with an empty body.

#### 2. Session grouping on the tracing helper

**File**: `backend/src/adapters/out/llm/tracing.py`

**Intent**: Let every observation from one capture session land in one Langfuse bucket, so a
conversation reads as a single thread rather than scattered spans.

**Contract**: `observation(...)` gains a keyword-only `session_id: str | None = None`; when present it
sets the `langfuse.session.id` attribute on the span. Existing callers are unaffected — the parameter
defaults to `None` and `OpenRouterEmbeddingAdapter` is not required to pass it.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run python -c "import adapters.out.llm.capture.agent"` succeeds
- `cd backend && uv run pytest tests/unit/capture/test_openrouter_embedding_adapter.py -v` still passes

---

## Phase 6: Pydantic AI adapter — stream mapping and tracing

### Overview

Map a Pydantic AI run onto capture's own event vocabulary, with the phase's tools supplied per call
and the whole turn traced into one session bucket. Proven with `TestModel` and `FunctionModel`; no
network call.

### Changes Required:

#### 1. Stream mapping

**File**: `backend/src/adapters/out/llm/capture/agent.py`

**Intent**: Translate the library's stream into `CaptureEvent`s so nothing from the adapter's world
crosses the port, which is FR-09.

**Contract**: `converse` builds a `FunctionToolset` from the tools it was handed and passes it to
`agent.run_stream_events(..., toolsets=[...])`. A `PartDeltaEvent` carrying a `TextPartDelta` becomes
`ReplyProduced` while conversing and `NoteContentProduced` while drafting. A `ToolResultEvent` is
mapped by its result's pinned `tool` discriminator onto the matching event —
`SessionTopicProposed`, `NoteTopicProposed`, `NoteTagProposed`, `DraftingConsentSignalled`,
`ConversationRequested`. The whole run is wrapped in `observation("capture_turn",
observation_type="agent", input_value=..., session_id=str(turn.session.id.value))`, recording model
and usage. Tool handlers are invoked with the same `turn` the adapter received.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/test_pydantic_ai_capture_agent.py -v` passes
- `cd backend && uv run pytest tests/unit/capture/contracts/test_capture_agent_contract.py -v` passes
- `cd backend && uv run basedpyright src/adapters` reports zero errors

#### Manual Verification:
- Run one capture turn against a real provider with `LANGFUSE_*` and `OPENROUTER_API_KEY` set, then
  open Langfuse and confirm every observation from that turn is grouped under the session id rather
  than appearing as separate traces.

---

## Phase 7: Deterministic in-memory capture agent adapter (stubs)

### Overview

Materialize the in-memory implementation of the same port.

### Changes Required:

#### 1. Adapter skeleton

**File**: `backend/src/adapters/out/in_memory/capture/capture_agent.py`

**Intent**: Declare the deterministic stand-in ahead of its behaviour.

**Contract**: `DeterministicCaptureAgentAdapter` exposing the same `converse` signature as
`CaptureAgentPort`, with an empty body.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run python -c "import adapters.out.in_memory.capture.capture_agent"` succeeds

---

## Phase 8: Deterministic adapter behaviour and message history

### Overview

Give the stand-in behaviour that keeps every acceptance scenario running, and close the port violation
the contract-shaping session left behind.

### Changes Required:

#### 1. Deterministic stand-in

**File**: `backend/src/adapters/out/in_memory/capture/capture_agent.py`

**Intent**: Drive the existing acceptance scenarios off the graph rather than off a mode machine of
the adapter's own.

**Contract**: `converse` yields events derived from `turn` and the tools it was offered. Recognising
`"that's all"` in the latest user message yields a `DraftingConsentSignalled` — a tool result, not a
phase decision; the adapter never inspects or sets `session.phase`. While the offered tools include
the note proposals, it yields `NoteTopicProposed`, `NoteTagProposed` and chunked
`NoteContentProduced`; otherwise it yields chunked `ReplyProduced`. The behaviour previously in
`_derive_topic_label`, `_derive_tag_labels` and `_derive_note_body` moves here; `_should_draft` and
`_CONFIRMATION_PHRASES` do not survive as a drafting decision.

#### 2. Message history

**File**: `backend/src/adapters/out/in_memory/capture/message_repository.py`,
`backend/tests/unit/capture/contracts/test_message_repository_contract.py`

**Intent**: Satisfy `MessageRepository` again and re-enable the suite that proves it.

**Contract**: `async def history(self, session_id: SessionId) -> list[Message]` returning the store's
messages for that session, empty list when none. The module-level `pytestmark` skip is removed.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/contracts/test_message_repository_contract.py -v` passes with nothing skipped
- `cd backend && uv run pytest tests/unit/capture/contracts/test_capture_agent_contract.py -v` passes for both implementations
- `cd backend && uv run basedpyright src tests` reports zero errors

---

## Phase 9: Command rewrite — one port and the turn loop

### Overview

Rebuild `GenerateReplyCommand` around `CaptureAgentPort` and the machine, replacing the single
straight-through stream with a loop that closes a segment when a move becomes available and opens the
next against the new phase's tools.

### Changes Required:

#### 1. Command signature and loop

**File**: `backend/src/application/capture/commands/send_message.py`

**Intent**: Give the command exactly one model-facing port and let the graph own every mode decision
it used to make itself.

**Contract**: The constructor takes `capture_sessions`, `uow`, `capture_agent: CaptureAgentPort` and
`vocabulary`, dropping `transcript_query`, `topic_extraction`, `confidence_assessment` and
`reply_generation`. `handle` rehydrates the session, builds a `CaptureTurn` from it plus
`uow.messages.history(...)`, constructs a `CaptureMachine` over it, and loops: get the current phase's
tools, open a stream inside `contextlib.aclosing`, apply each arriving event to the machine while
translating it to the client's `ReplyStreamEvent` shape, and break the segment when
`machine.can_advance(event)`. Outside the segment, `await machine.advance(event)` and loop again;
terminate when no move is available or a bounded iteration count is reached. The session, its
messages and any note the turn touched are read off `machine.context` and persisted once, then
`uow.commit()`. Any exception propagates out of the `async with uow` block uncommitted, so an
interrupted turn leaves no trace — the rollback posture chosen in planning.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/test_send_message_command.py -v` passes
- `cd backend && uv run basedpyright src/application` reports zero errors

#### Manual Verification:
- `cd backend && uv run fastapi dev src/main.py`, then start a session and `curl -N` the send-message
  endpoint twice — once with ordinary content, once with `"that's all"` — and confirm the second
  response streams reply text followed by draft events within the same request.

---

## Phase 10: Remove the superseded ports and rewire composition

### Overview

Delete what `CaptureAgentPort` replaces, repoint the container, and bring integration and acceptance
suites back to green. Cleanup only — no new behaviour and no new tests.

### Changes Required:

#### 1. Port and adapter removal

**File**: `backend/src/application/capture/ports.py`,
`backend/src/application/capture/value_objects.py`,
`backend/src/adapters/out/in_memory/capture/{reply_generation,topic_extraction,confidence_assessment}.py`,
`backend/tests/unit/capture/contracts/test_confidence_assessment_contract.py`

**Intent**: Leave exactly one route from the application to a model.

**Contract**: `TopicExtractionPort`, `ConfidenceAssessmentPort` and `ReplyGenerationPort` are removed
along with their deterministic adapters and contract suites. The `ReplyChunk` union and its members
are removed from `application/capture/value_objects.py`; `ConfidenceAssessment`, `ConfidencePoint`,
`Transcript` and `TranscriptEntry` are kept only where something still reads them, and removed
otherwise.

#### 2. Composition and downstream suites

**File**: `backend/src/adapters/compose.py`, `backend/src/config/settings.py`,
`backend/tests/integration/`, `backend/tests/bdd/`

**Intent**: Wire the new port the way the embedding port is already wired, and confirm nothing
downstream regressed.

**Contract**: `Settings` gains `capture_agent_provider: CaptureAgentProvider = DETERMINISTIC` and a
model name, mirroring `embedding_provider`. A `_build_capture_agent_port(settings)` branches between
the deterministic and Pydantic AI adapters exactly as `_build_embedding_port` does at line 143, so CI
needs no key. `get_generate_reply_command` passes the single port. Integration and BDD suites are
updated only where the removed symbols or the changed constructor made them fail.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest` passes across every suite, including `tests/features/distill-flow/`
- `cd backend && uv run ruff check src tests` is clean
- `cd backend && uv run basedpyright src tests` reports zero errors
- `cd backend && grep -rn "ReplyGenerationPort\|TopicExtractionPort\|ConfidenceAssessmentPort\|ReplyChunk" src tests` returns nothing

#### Manual Verification:
- `cd backend && uv run fastapi dev src/main.py`, then walk one session from first message through
  `"that's all"` to a drafted note, confirming the SSE event sequence is unchanged from the client's
  point of view.

## Testing Strategy

### Unit Tests:
Mechanics (phases 1–2) are proven against a throwaway two-phase graph that is not capture's, so
reusability is tested rather than asserted. Capture's own graph (phase 4) is tested for its guards,
its per-turn tool filtering, and two invariants `frame.md` demands: `graph.terminal_states` is empty,
and both edges stay reachable. Adapter tests (6, 8) use `TestModel`/`FunctionModel` and the real
in-memory store respectively. Command tests (9) cover the single-segment turn, the transition turn
with two segments, and rollback on a mid-stream failure.

### Integration Tests:
`tests/integration/test_capture_http.py` exercises the SSE contract unchanged; phase 10 updates it
only where removed symbols force it.

### Manual Testing Steps:
Per-phase Manual bullets above. The Langfuse session-grouping check in phase 6 is the one step that
cannot be automated here, since it requires a real provider call and the Langfuse UI.

## Performance Considerations

A turn that crosses a phase costs two model calls instead of one, bounded by the iteration cap. Turns
that cross nothing — the common case — cost exactly one, as today. `uow.messages.history(...)` adds a
read per turn that replaces the `TranscriptQueryPort` read it displaces, so the count is unchanged.

## Migration Notes

No persisted data changes shape: `CaptureSession.phase` already defaults to `CONVERSING` and
`drafting_consent` defaults to `None`, so existing sessions rehydrate into a legal state. The HTTP
event vocabulary in `application/capture/dto.py` is untouched, so no client changes.

## References

- `context/changes/llm-adapter-capture-modes/frame.md` — boundaries and FR-01…FR-04
- `context/changes/llm-adapter-capture-modes/discover-contracts-log.md` — the shaping session's
  decisions, and what it explicitly carried to this plan
- `context/efforts/llm-adapter/research-pydantic-ai.md` — library surface and adapter boundary
- `context/efforts/llm-adapter/research-langfuse.md` — sessions group traces
- `context/adrs/hexagonal-arch-shape/decision.md` — layering, `UnitOfWork` ownership, InMemoryFirst
- `context/foundation/rules/layering.md`, `contract-testing.md`, `exceptions.md`
- `context/foundation/testing-conventions.md`
