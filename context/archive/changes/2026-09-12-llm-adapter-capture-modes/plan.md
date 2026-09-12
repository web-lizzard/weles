# Capture Capture-Mode Graph and the Pydantic AI Agent Adapter — Implementation Plan

> Revision 2 (2026-09-12): the machine reports available transitions and the command decides; guards read disjoint intents off the aggregate instead of the event, and each edge consumes the intent that let it through. Phase 1 is executed and untouched; phase 2 is split into a stubs and a behaviour phase, shifting later phases by one. Prior version: plan-versions/v1-plan.md
> Revision 3 (2026-09-12): a turn's own messages reach the machine as command-raised events, and the event union splits so an adapter cannot raise them. Phases 1-5 are executed and untouched; new phases 6 and 7 are inserted before the adapter work, shifting later phases by two. Prior version: plan-versions/v2-plan.md
> Revision 4 (2026-09-12): actions receive a dependency set, so vocabulary resolution and note construction move out of the command and into the drafting phase that owns them. Phases 1-13 are untouched; the work appends as phases 14-17. Prior version: plan-versions/v3-plan.md

## Overview

Slice S-02 of the `llm-adapter` effort makes the effort's thesis falsifiable: the phases of a
capture session and the legal moves between them become domain artifacts, and the model reaches
them only through tools. `/discover-contracts` already put the mechanics and the capture graph on
disk as declarations with empty bodies. This plan fills those bodies, completes the consent model
in the shape the planning session settled, rewrites `GenerateReplyCommand` onto a single
`CaptureAgentPort`, and builds two adapters behind that port — the Pydantic AI one first.

The working tree is knowingly red at the start: `InMemoryMessageRepository` no longer satisfies
`MessageRepository`, and its contract suite is skipped. Phase 11 closes that.

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

Bottom-up, because each layer's tests need the one below to exist. Mechanics first (phases 1–3),
then the capture composition's consent and return model (3–4), then the adapters behind the already
declared port (5–8) with Pydantic AI ahead of the in-memory one at the user's direction, then the
command that consumes all of it (9), then removal of what the new seam replaces (10).

Stubs phases appear only where a test would otherwise fail to collect. Phases 1, 3, 5, 7, 11 and 12
add methods or behaviour to classes and modules that already exist — a test importing them collects
and fails on behaviour, which is the red half doing its job. Phases 2, 4, 6, 8 and 10 introduce
symbols the suites import by name — new aliases, new classes, new modules — so each is a stubs phase
of its own.

## Critical Implementation Details

Guards read state, never the event. An intent — consent to draft, or a request to return to
conversation — is persisted on the session by an action during `apply`, and the edge that it permits
**consumes** it. That consumption is what terminates the loop: once an intent is spent, nothing
permits a further move until the model produces a new one. Guarding the return edge is still
required, but for a narrower reason than an earlier draft of this plan claimed — without it, every
drafting turn would burn one extra segment returning to a conversation nobody asked for.

Because guards are disjoint by construction, at most one transition is ever available. Two available
at once means the intents stopped being disjoint, which is a defect in the graph declaration — caught
by the mechanics suite, not raised at runtime, per the `graph-exceptions` decision.

The command asks the machine what is available and decides for itself; it never asks the machine to
pick. That is what keeps a future in which the *model* chooses the next phase from requiring a
different shape — it reads the same list, by description.

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

## Phase 2: Edge vocabulary and state descriptions (stubs)

### Overview

Materialize the contract phase 3's tests import. A guard now runs after a whole stream segment, when
no event requests the move, so the edge-side callables lose their event parameter — and the graph's
own test suite imports those aliases by name, so they must exist before a test can collect.

### Changes Required:

#### 1. Edge aliases and state description

**File**: `backend/src/domain/shared/graph/model.py`

**Intent**: Separate what an edge sees from what a phase sees, and give a state the description a
model will one day read when it chooses where to go next.

**Contract**: `EdgeCondition[ContextT]` taking only the context and returning `bool`;
`EdgeAction[ContextT]` taking only the context and returning an awaitable. `Transition.guard` becomes
`EdgeCondition[ContextT] | None` and `Transition.actions` becomes `Sequence[EdgeAction[ContextT]]`.
`Condition` and `Action` keep their event parameter and stay in use for `State.get_actions`, which
still runs per event. `State` gains an abstract `description: str` property, the state-level
counterpart of `Tool.description`. This supersedes the `guard-concept` entry in
`discover-contracts-log.md`, whose premise — that a guard is evaluated against the event requesting
the move — no longer holds.

#### 2. State machine surface

**File**: `backend/src/domain/shared/graph/machine.py`

**Intent**: Declare the reporting surface before giving it behaviour.

**Contract**: `current_state_name -> NameT` and `available_transitions() -> Mapping[NameT, str]`
declared with empty bodies. `transition(target) -> bool` loses its event parameter. `can_transition`
is removed: membership in `available_transitions()` answers the same question, and two ways to learn
one fact drift apart. `can_advance` and `advance` are never introduced.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run python -c "from domain.shared.graph.model import EdgeCondition, EdgeAction"` succeeds
- `cd backend && uv run basedpyright src/domain/shared/graph` reports zero errors

---

## Phase 3: State machine behaviour — reporting available transitions

### Overview

Fill `StateMachine` so it reports what is available and moves when told, without ever choosing.

### Changes Required:

#### 1. State machine

**File**: `backend/src/domain/shared/graph/machine.py`

**Intent**: Let the machine answer "where can this context go from here, and what are those places"
while leaving the choice to the caller.

**Contract**: `__init__(context)` stores the context; `context`, `current_state` and
`current_state_name` expose it, the resolved `State`, and its name. `get_tools()` delegates to the
current state. `apply(event)` runs the actions the current state warrants for that event and crosses
no edge. `available_transitions()` returns every target whose edge guard passes, mapped to that
target state's `description` — the keys are what a command matches on, the values are what a model
would read. `transition(target)` runs the edge's actions, writes the new name via `enter_state`, and
reports whether the move happened; it refuses a target that is not currently available. Remove both
blocking comments.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/shared/test_graph_machine.py -v` passes
- `cd backend && uv run pytest tests/unit/shared/test_graph_model.py -v` still passes after the alias split
- `cd backend && uv run basedpyright src/domain/shared/graph` reports zero errors

---

## Phase 4: Consent and return-to-conversation symbols (stubs)

### Overview

Materialize the symbols phase 5's tests import. No behaviour — declarations and empty bodies only.

### Changes Required:

#### 1. Consent value object on the session

**File**: `backend/src/domain/capture/value_objects.py`, `backend/src/domain/capture/capture_session.py`

**Intent**: Give the session a durable carrier for the user's expressed wish to draft, so it survives
between turns the way the phase itself does.

**Contract**: `DraftingConsent(BaseModel, frozen=True)` and `ConversationRequest(BaseModel, frozen=True)`
in `value_objects.py` — two disjoint intents, so at most one guard can ever pass.
`CaptureSession.drafting_consent: DraftingConsent | None = None` and
`CaptureSession.conversation_request: ConversationRequest | None = None`, plus
`record_drafting_consent`, `record_conversation_request`, and `clear_drafting_consent` /
`clear_conversation_request` — all with empty bodies. The clearers exist because an intent is spent
when the edge it permits is taken.

#### 2. Tools, results and events

**File**: `backend/src/domain/capture/graph.py`, `backend/src/domain/capture/turn.py`

**Intent**: Declare the two recognitions — consent to draft, and the request to return to
conversation — as tools with results and matching domain events.

**Contract**: In `graph.py`: `DraftingConsentSignal(ToolResult, frozen=True)` pinning
`tool: Literal["signal_drafting_consent"]`; `ConversationRequestSignal(ToolResult, frozen=True)`
pinning `tool: Literal["request_conversation"]`; handlers `_signal_drafting_consent` and
`_request_conversation`; module-level `_SIGNAL_DRAFTING_CONSENT` and `_REQUEST_CONVERSATION` tools;
phase actions `_record_drafting_consent` and `_record_conversation_request`; edge actions
`_consume_drafting_consent` and `_consume_conversation_request`; guard `conversation_requested`;
`description` on `Conversing` and `Drafting`. In `turn.py`:
`DraftingConsentSignalled` and `ConversationRequested` event models, both added to the `CaptureEvent`
union; `TurnOpened` is removed along with its `consent_signalled` field.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run python -c "import domain.capture.graph, domain.capture.turn"` succeeds
- `cd backend && uv run basedpyright src/domain/capture` reports zero errors

---

## Phase 5: Capture graph behaviour — guards, actions and tool filtering

### Overview

Make capture's composition decide things: when consent counts, when a return is permitted, which
tools a phase offers this turn, and what an event makes happen.

### Changes Required:

#### 1. Guards and the consent action

**File**: `backend/src/domain/capture/graph.py`, `backend/src/domain/capture/capture_session.py`

**Intent**: Move the drafting decision out of the adapter's phrase list and the topic decision off the
command, into the graph where `frame.md` puts them.

**Contract**: `consent_given(context)` returns true when `context.session.drafting_consent` is set —
an `EdgeCondition`, so it reads persisted state and takes no event. `conversation_requested(context)`
returns true when `context.session.conversation_request` is set. The two are disjoint by
construction, because each edge clears its own intent on the way through.
`_record_drafting_consent(context, event)` persists the consent only when `context.messages` is
non-empty — the invariant that keeps a consent without a conversation from being recorded — and
`_record_conversation_request` persists the return intent. The edge actions
`_consume_drafting_consent` and `_consume_conversation_request` clear them, and are what makes an
intent single-use and the command's loop finite.

#### 2. Phase inventories and filtering

**File**: `backend/src/domain/capture/graph.py`

**Intent**: Let each phase narrow its own tool set per turn, and run only the actions an event warrants.

**Contract**: `Conversing.tools` gains `_SIGNAL_DRAFTING_CONSENT`; `Conversing.get_tools` withholds
`_PROPOSE_SESSION_TOPIC` once `context.session.topic` is set — the filter `send_message.py:83`
performs today. `Conversing.get_actions` returns `_assign_session_topic` only for a
`SessionTopicProposed` and `_record_drafting_consent` only for a `DraftingConsentSignalled`.
`Drafting.tools` gains `_REQUEST_CONVERSATION`, and `Drafting.get_actions` returns
`_record_conversation_request` only for a `ConversationRequested`. `_assign_session_topic` puts the
proposed topic on the session. The `CONVERSING -> DRAFTING` transition carries
`actions=(_consume_drafting_consent,)` and the `DRAFTING -> CONVERSING` transition gains
`guard=conversation_requested` with `actions=(_consume_conversation_request,)`; the in-file comment
justifying the missing guard is replaced with one explaining why it is required — without it every
drafting turn burns a segment returning to a conversation nobody asked for. Both states get a
`description`. The five proposal handlers return their results from the arguments the model sent.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/test_capture_graph.py -v` passes, including that at most one transition is ever available
- `cd backend && uv run pytest tests/unit/capture/test_model.py -v` passes
- `cd backend && uv run basedpyright src/domain` reports zero errors

### Review r5

Artifact: `reviews/2026-09-12-r5-mutation-test-phases-5-6-7-.md`

- `R5-F2` — Capture graph tests must assert `CaptureSession.start()` stamps UTC-aware `created_at`
  Fix: A capture graph test that uses `CaptureSession.start()` must assert `created_at.tzinfo is UTC` so mutmut’s dependency-selected suite catches naive timestamps

---

## Phase 6: Message-recording events and the agent/command event split (stubs)

### Overview

Materialize the symbols phase 7's tests import. Two events the *command* raises — not the adapter —
plus the union split that stops an adapter from raising them.

### Changes Required:

#### 1. Event split and the two message events

**File**: `backend/src/domain/capture/turn.py`

**Intent**: A turn's own messages never reach the machine today, so the context a tool reads is the
conversation minus its latest exchange. These two events are how they get there; splitting the union
is how the type system keeps them out of the adapter's hands.

**Contract**: `UserMessageRecorded` and `AssistantMessageRecorded`, each `frozen=True` with a pinned
`kind` literal and a `message: Message` field. `AgentEvent` becomes the union of everything the model
produces — `ReplyProduced`, `SessionTopicProposed`, `NoteTopicProposed`, `NoteTagProposed`,
`NoteContentProduced`, `DraftingConsentSignalled`, `ConversationRequested` — and
`CaptureEvent = AgentEvent | UserMessageRecorded | AssistantMessageRecorded` is what the command
applies. `CaptureTurn` gains `record_message(self, message: Message) -> None`, empty body, so
appending stays the context's own operation rather than the caller reassigning a field.

#### 2. Port narrowing and action declarations

**File**: `backend/src/domain/capture/ports.py`, `backend/src/domain/capture/graph.py`

**Intent**: Make "the adapter cannot raise a command event" a type error rather than a convention.

**Contract**: `CaptureAgentPort.converse` returns `AsyncIterator[AgentEvent]`. In `graph.py`, actions
`_record_user_message` and `_record_assistant_message` with empty bodies.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run python -c "from domain.capture.turn import AgentEvent, UserMessageRecorded, AssistantMessageRecorded"` succeeds
- `cd backend && uv run basedpyright src/domain/capture` reports zero errors

---

## Phase 7: A turn's own messages reach the machine

### Overview

Make the two events do their work, so the context a tool reads includes the exchange in progress.

### Changes Required:

#### 1. Recording actions, offered by both phases

**File**: `backend/src/domain/capture/graph.py`, `backend/src/domain/capture/turn.py`

**Intent**: A message is part of the conversation whatever phase the session is in, so both states
run these actions; and the consent invariant finally has the message it tests for.

**Contract**: `CaptureTurn.record_message` appends to `messages` in memory. `_record_user_message` and
`_record_assistant_message` call it with the event's message. Both `Conversing.get_actions` and
`Drafting.get_actions` return the matching recorder for a `UserMessageRecorded` or an
`AssistantMessageRecorded`, alongside the actions each already returns; both inventories grow to
match. This closes two defects: `_record_drafting_consent` currently sees an empty `context.messages`
when the user's first message is the consent, and `propose_note_content` currently drafts from a
conversation missing its latest exchange.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/test_capture_graph.py -v` passes, including consent recorded when the turn's own message is the only one
- `cd backend && uv run basedpyright src/domain` reports zero errors

---

## Phase 8: Pydantic AI capture agent adapter (stubs)

### Overview

Materialize the adapter module and class phase 9's tests import.

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

## Phase 9: Pydantic AI adapter — stream mapping and tracing

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

## Phase 10: Deterministic in-memory capture agent adapter (stubs)

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

## Phase 11: Deterministic adapter behaviour and message history

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

## Phase 12: Command rewrite — one port and the turn loop

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
`uow.messages.history(...)`, constructs a `CaptureMachine` over it, and runs at most
`_MAX_SEGMENTS = 2` segments — the number this use case needs, conversing then drafting, declared as
a constant in the command rather than as a tuned setting. Each segment first attempts the transition
this use case cares about, then streams:

```python
for _ in range(_MAX_SEGMENTS):
    available = machine.available_transitions()
    if CapturePhase.DRAFTING in available:
        await machine.transition(CapturePhase.DRAFTING)
    async for event in agent.converse(turn, machine.get_tools()):
        await machine.apply(event)
        yield ...                       # text passes through in the same pass
```

Before the first segment the command records the user's message and applies a `UserMessageRecorded`;
after a segment whose reply buffer is non-empty it records the assistant's message and applies an
`AssistantMessageRecorded`, so the drafting segment reads a complete conversation. The transition is
attempted at the *start* of a segment, not the end, so an intent recorded in a previous turn is
consumed before the model is handed the wrong phase's tools. The command names the
phase it wants and matches on it declaratively — that is its use case, not the graph's topology, so
adding a phase this command does not serve changes nothing here. The session, its messages and any
note the turn touched are read off `machine.context` and persisted once, then `uow.commit()`. Any
exception propagates out of the `async with uow` block uncommitted, so an interrupted turn leaves no
trace — the rollback posture chosen in planning. `contextlib.aclosing` wraps each segment as hygiene
on that exception path, not as a mid-stream break mechanism.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/test_send_message_command.py -v` passes
- `cd backend && uv run pytest tests/unit/capture/test_send_message_command.py -k segments -v` confirms no turn opens a third segment
- `cd backend && uv run basedpyright src/application` reports zero errors

#### Manual Verification:
- `cd backend && uv run fastapi dev src/main.py`, then start a session and `curl -N` the send-message
  endpoint twice — once with ordinary content, once with `"that's all"` — and confirm the second
  response streams reply text followed by draft events within the same request.

---

## Phase 13: Remove the superseded ports and rewire composition

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

## Phase 14: Dependencies reach actions

### Overview

Give the graph mechanics a dependency parameter so an action can do the work an action is for. Today
an action can only mutate what the context already holds; anything needing a repository or an
embedding has to happen in the command instead, which is why `Drafting` has no actions at all.

### Changes Required:

#### 1. A fourth type parameter across the mechanics

**File**: `backend/src/domain/shared/graph/model.py`

**Intent**: Actions receive collaborators; conditions and tools do not.

**Contract**: `Action[ContextT, DepsT, EventT] = Callable[[ContextT, DepsT, EventT], Awaitable[None]]`
and `EdgeAction[ContextT, DepsT] = Callable[[ContextT, DepsT], Awaitable[None]]`. `Condition` and
`EdgeCondition` keep their context-only signature — a guard reads intent persisted on the aggregate
and has nothing to fetch, which is what revision 2 settled. `Tool` and `ToolHandler` are unchanged:
tools read and compute over the context, and whatever a future tool needs will be a different set of
dependencies than an action's. `State[ContextT, DepsT, EventT]`, `Transition[ContextT, DepsT, EventT]`
and `Graph[ContextT, DepsT, EventT, NameT]` propagate the parameter.

#### 2. The machine carries and forwards them

**File**: `backend/src/domain/shared/graph/machine.py`

**Intent**: One place holds the dependencies for a turn.

**Contract**: `StateMachine[ContextT, DepsT, EventT, NameT]` takes `__init__(self, context, deps)` and
exposes a `deps` property beside `context`. `apply` calls each action as `action(context, deps, event)`;
`transition` calls each edge action as `action(context, deps)`. Nothing else about either method moves —
`apply` still crosses no edge, and `transition` still refuses an unreachable target with `False`.

#### 3. Existing compositions widen without changing

**File**: `backend/src/domain/capture/graph.py`,
`backend/src/application/capture/commands/send_message.py`

**Intent**: Prove the widening is behaviour-free before any behaviour moves onto it.

**Contract**: Every action in `graph.py` takes the new parameter and ignores it; `CaptureMachine`
becomes `StateMachine[CaptureTurn, CaptureDeps, CaptureEvent, CapturePhase]`, and the command
constructs it with a deps object. No action reads a dependency in this phase.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/shared/` passes, including a spy action asserting the deps
  object it was handed is the one the machine was built with, on both `apply` and `transition`
- `cd backend && uv run pytest tests/unit/capture/` passes unchanged — no capture behaviour moved
- `cd backend && uv run basedpyright src tests` reports zero errors

## Phase 15: Vocabulary resolution and the dependency set move into the domain (stubs)

### Overview

Put the symbols the drafting actions will need where the domain can import them. Relocation and new
declarations only — every moved body is moved verbatim.

### Changes Required:

#### 1. The embedding port and the resolver become domain

**File**: `backend/src/domain/capture/ports.py`, `backend/src/domain/capture/vocabulary.py`,
`backend/src/application/capture/ports.py`,
`backend/src/application/capture/services/vocabulary.py`

**Intent**: Stop routing domain work through the application because of where a file sits.

**Contract**: `EmbeddingPort` moves to `domain/capture/ports.py` — it is `embed(text) -> Embedding`
over a domain value object and owes nothing to the application. `VocabularyResolver` moves to
`domain/capture/vocabulary.py`, beside the `MatchCriteria` it already uses, and `ResolvedTopic` /
`ResolvedTag` move with it. Both take `TopicRepository` / `TagRepository` as arguments today, and
those were already domain ports, so no port is being invented — this is a relocation, not a
concession. `application/capture/services/vocabulary.py` is removed and importers repointed.

#### 2. The dependency set

**File**: `backend/src/domain/capture/deps.py`

**Intent**: Name exactly what a capture action may reach for.

**Contract**: `CaptureDeps` is a Protocol exposing `messages: MessageRepository`,
`notes: NoteRepository`, `topics: TopicRepository`, `tags: TagRepository`,
`note_vocabulary: NoteVocabularyRepository` and `vocabulary: VocabularyResolver`. It exposes no
`UnitOfWork` and no `commit` — every member is a domain repository port, and none of them has a
commit method, so an action cannot reach the transaction boundary even by mistake. The boundary is
held by the type, not by a convention an author has to remember.

#### 3. The note under construction

**File**: `backend/src/domain/capture/turn.py`, `backend/src/domain/capture/exceptions.py`

**Intent**: Carry a half-built note, which `Note` itself cannot represent.

**Contract**: `NoteDraft` is a mutable model with `topic: Topic | None`, `tags: list[Tag]` and
`content: str`, and `CaptureTurn` gains `draft: NoteDraft | None`. `Note` cannot stand in for it:
`NoteContent` rejects an empty value and `Note.draft` demands content, so no note exists at the
moment a topic is proposed. `DraftCompleted` joins the command-raised events beside the two message
events — the same mechanism revision 3 introduced, for the same reason: the end of a drafting
segment is something only the command knows. `DraftTopicMissingError` moves from
`application/capture/exceptions.py` to the domain.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run python -c "from domain.capture.deps import CaptureDeps; from domain.capture.turn import NoteDraft, DraftCompleted; from domain.capture.vocabulary import VocabularyResolver"` exits zero
- `cd backend && uv run pytest` passes — the relocation changes no behaviour
- `cd backend && uv run basedpyright src tests` reports zero errors

## Phase 16: Drafting actions build the note

### Overview

Move note construction out of `_TurnBuffers` and into the phase that owns it. This is the phase the
whole revision exists for: after it, `Drafting` is a state with actions rather than a state the
machine passes through while the command does the work.

### Changes Required:

#### 1. Actions for the three drafting events

**File**: `backend/src/domain/capture/graph.py`

**Intent**: Every event the drafting phase produces lands on the turn through `apply`.

**Contract**: `Drafting.get_actions` returns `_resolve_note_topic` on `NoteTopicProposed`,
`_resolve_note_tag` on `NoteTagProposed` and `_append_note_content` on `NoteContentProduced`.
`_resolve_note_topic` calls `deps.vocabulary.resolve_topic(event.label, deps.topics)` and opens
`context.draft` with the resolved topic; `_resolve_note_tag` resolves through `deps.tags` and appends;
`_append_note_content` concatenates onto `draft.content`. A tag or content event arriving while
`context.draft` is `None` raises `DraftTopicMissingError` — the ordering invariant now belongs to the
state that holds it, instead of being three `if resolved_topic is None` checks in the handler.

#### 2. Materialisation and persistence

**File**: `backend/src/domain/capture/graph.py`

**Intent**: Turn the accumulated draft into a note once the segment that fills it is over.

**Contract**: `_materialise_note` runs on `DraftCompleted`. With no draft it does nothing. With a
draft it either calls `session.draft_note(topic, NoteContent(value=content), tags)` or, when the
session already has a note, re-topics, reconciles tags and updates content on the note read through
`deps.notes` — the redraft logic lifted out of `_apply_redraft`, unchanged in substance. It then
stages the note with `deps.notes.add(note)` and puts it on `context.note`. The two message actions
stage through `deps.messages.add` in the same way. Staging only: nothing here commits, because
nothing here can.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/test_capture_graph.py` passes, covering a first
  draft, a redraft over an existing note, and `DraftTopicMissingError` on a tag before a topic
- `cd backend && uv run pytest tests/unit/capture/` passes
- `cd backend && uv run basedpyright src tests` reports zero errors

## Phase 17: The command stops resolving vocabulary

### Overview

Collapse `_TurnBuffers` to what the SSE stream actually needs and let the command do what a command
does: build the dependency set, run the loop, map events to DTOs, commit.

### Changes Required:

#### 1. Deps assembly and a pure mapping

**File**: `backend/src/application/capture/commands/send_message.py`

**Intent**: One await per event in the stream loop, not two.

**Contract**: Inside `async with self._uow as uow` the command builds a `CaptureDeps` from the unit of
work's repositories plus the injected `VocabularyResolver`, and constructs
`CaptureMachine(turn, deps)`. `_map_agent_event` becomes synchronous and pure: event in, stream DTO
out, no repository reached. `_TurnBuffers` keeps only `full_text` and `agent_message`, both of which
exist for `ReplyDoneEvent` — `resolved_topic`, `resolved_tags` and `draft_text` are gone, since the
turn now holds them. The command raises `DraftCompleted` after a drafting segment closes, alongside
the `AssistantMessageRecorded` it already raises.

#### 2. Persistence and the commit boundary

**File**: `backend/src/application/capture/commands/send_message.py`

**Intent**: Keep the commit where CQRS-lite puts it.

**Contract**: The tail loop that diffed `context.messages` against `prior` and called
`uow.messages.add` / `uow.notes.add` is removed — actions staged those. `await uow.capture_sessions.save(session)`
and `await uow.commit()` stay exactly where they are, and stay the only commit in the change.
`DraftDoneEvent` is built from `context.note` and `context.draft` rather than from buffers.
`_apply_redraft` is deleted.

#### 3. Composition

**File**: `backend/src/adapters/compose.py`

**Intent**: Follow the moved symbols.

**Contract**: Import sites for `VocabularyResolver`, `EmbeddingPort`, `ResolvedTopic` and
`ResolvedTag` point at the domain. `get_generate_reply_command` is otherwise unchanged — the resolver
was already constructed there and injected.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/test_send_message_command.py` passes, including a
  turn that drafts and a turn that redrafts over an existing note
- `cd backend && uv run pytest` passes across every suite
- `cd backend && uv run ruff check src tests` is clean
- `cd backend && uv run basedpyright src tests` reports zero errors
- `cd backend && grep -rn "_TurnBuffers" src | grep -c "resolved_topic\|resolved_tags\|draft_text"` returns 0

#### Manual Verification:
- `cd backend && uv run fastapi dev src/main.py`, then walk one session through to a drafted note and
  confirm the `DraftTopicEvent` / `DraftTagEvent` / `DraftDeltaEvent` sequence is unchanged.

## Testing Strategy

### Unit Tests:
Mechanics (phases 1–3) are proven against a throwaway two-phase graph that is not capture's, so
reusability is tested rather than asserted. Capture's own graph (phases 5 and 7) is tested for its guards,
its per-turn tool filtering, and two invariants `frame.md` demands: `graph.terminal_states` is empty,
and both edges stay reachable. Adapter tests (9, 11) use `TestModel`/`FunctionModel` and the real
in-memory store respectively. Command tests (12) cover the single-segment turn, the transition turn
with two segments, and rollback on a mid-stream failure.

### Integration Tests:
`tests/integration/test_capture_http.py` exercises the SSE contract unchanged; phase 13 updates it
only where removed symbols force it.

### Manual Testing Steps:
Per-phase Manual bullets above. The Langfuse session-grouping check in phase 9 is the one step that
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
