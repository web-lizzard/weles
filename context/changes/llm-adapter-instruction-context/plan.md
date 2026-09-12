# Capture Instruction Context Implementation Plan

## Overview

Capture's model-facing prose becomes a domain artifact. Each phase of the capture graph
builds an `Instruction` — an ordered tuple of named blocks with a declared required set —
from the context the turn already carries, and hands it across `CaptureAgentPort` beside the
tools. Both adapters render what they are given and hold no prose of their own. Assessed
coverage reaches the domain as an event, survives on the session, and is read back out as a
word (`CoverageReading`), never as the float the model sent.

The contract-shaping session (`discover-contracts-log.md`) already put the types, the builder
hierarchy and the prose on disk. This plan implements the bodies it deliberately left, adds
the wiring no session has written yet, and pins the whole surface with unit tests.

## Current State Analysis

Landed by the contract session in `dd41b36`, complete and unexercised:

- `backend/src/domain/shared/instruction/model.py` — `InstructionBlock` (with the guarded
  `rendered` classmethod), `Instruction` (required-set validator, `blocks` as a tuple), and
  the `InstructionBuilder[ContextT]` protocol. **Bodies are finished; there is no test file.**
- `backend/src/domain/capture/value_objects.py` — `Coverage`, `CoverageTrend` (3 members),
  `CoverageReading` (4 members).
- `backend/src/domain/capture/capture_session.py` — `assessments: tuple[Coverage, ...]` and
  `record_assessment`.
- `backend/src/adapters/http/errors.py` — `coverage_out_of_range → 422`.

Left as empty bodies on purpose:

- `CaptureInstructionBuilder.build`, `ConversingInstructionBuilder.phase_blocks`,
  `DraftingInstructionBuilder.phase_blocks` (`backend/src/domain/capture/instructions.py`).
- `trend_of`, `reading_of` (`backend/src/domain/capture/coverage.py`, `NotImplementedError`).

Missing entirely — no symbol exists:

- A hook by which the machine asks the current phase for its instruction.
- An `instruction` parameter on `CaptureAgentPort.converse`.
- A `CoverageAssessed` *event*. The name is currently taken by the `ToolResult` in
  `backend/src/domain/capture/graph.py`, which carries a bare `float` and reaches nothing:
  no action consumes it and `_event_from_tool_result` does not map it.
- Any consumption of a block by either adapter.
  `backend/src/adapters/out/llm/capture/agent.py` selects between two module constants with
  `_instructions_for`'s `if` on the phase; `backend/src/adapters/out/in_memory/capture/capture_agent.py`
  holds `_HANDOFF_LINE`, `_DEFAULT_SOLID` and `_DEFAULT_SHAKY` and infers its phase from the
  tool set it was handed.

### Key Discoveries:

- `discover-contracts-log.md` **overrides `frame.md` on one sentence**: coverage shapes tone,
  never capability. No block may gate a tool, and no test may assert the model cannot signal
  drafting consent at low coverage.
- `State` declares `tools` as an abstract inventory and filters per turn in `get_tools`
  (`backend/src/domain/shared/graph/model.py:100-131`). The instruction hook mirrors it
  exactly: an abstract `instruction_builder`, and `StateMachine.build_instruction` beside
  `StateMachine.get_tools` (`backend/src/domain/shared/graph/machine.py:45-52`).
- `_argument_type` (`backend/src/adapters/out/llm/capture/agent.py:181-190`) already unwraps a
  single-field `BaseModel` to its inner type when building a tool schema, so typing the tool
  result's field as `Coverage` still shows the model a plain `float`.
- pydantic-ai 2.35.3 accepts a sequence for `instructions=`: `AgentInstructions` in
  `pydantic_ai/_instructions.py` unions `Sequence[TemplateStr | str | SystemPromptFunc]`, and
  `normalize_instructions` flattens it. Block boundaries survive the port with no separator
  invented by the adapter.
- `turn.coverage_confidence` is written by the deterministic double
  (`capture_agent.py:102`) and read by `send_message.py:133` into `ReplyDoneEvent`. The BDD
  step `backend/tests/bdd/steps/coverage_wrapup.py:32` subclasses the double purely to set it.
- `CaptureAgentPort` has a contract suite parametrized over both implementations
  (`backend/tests/unit/capture/contracts/test_capture_agent_contract.py`), so the signature
  change lands on both at once.
- 11 fake `State` subclasses live in `backend/tests/unit/shared/` and
  `backend/tests/property/shared/`; an abstract `instruction_builder` touches every one.

## Desired End State

A capture turn dispatches an instruction that the domain built and no adapter authored.
Verified when:

- `cd backend && uv run pytest` is green, including a new suite for the shared instruction
  model, capture's coverage arithmetic and policy, and both phase builders.
- No prose constant remains in either capture adapter: `_CONVERSING_INSTRUCTIONS`,
  `_DRAFTING_INSTRUCTIONS`, `_HANDOFF_LINE`, `_DEFAULT_SOLID` and `_DEFAULT_SHAKY` are gone.
- A capture session run through the TUI still replies, still drafts on the user's word, and
  the reply's `done` event still carries `coverage_confidence` — now read from the session's
  last assessment rather than from a field the adapter wrote.

## What We're NOT Doing

- Rendering a phase's tools as provider-facing tool definitions — slice S-04 (FR-06, FR-07).
- Distill's instructions. `domain/shared/instruction/` is shaped by capture alone; that is
  the risk `frame.md` accepts.
- Any evaluation of whether an instruction produces *good* output — out of scope for the
  whole effort.
- A domain exception for FR-05's guard. The required-set failure stays a `ValueError`: it is
  broken by an author in a test, not by a user at runtime.
- Changing the HTTP or TUI contract. `ReplyDoneEvent.coverage_confidence` keeps its name,
  type and place; only its source changes.
- Reopening `frame.md` to absorb the contract session's override.

## Implementation Approach

Bottom-up, so every layer is exercisable before the one above it exists. The two pure
surfaces the contract session left unimplemented come first (coverage arithmetic, then the
builders that read it), each pinned by unit tests with no model and no adapter in the loop —
which is the whole argument for placing them in the domain. The new wiring symbols are
declared together in one stubs phase so the behaviour phases above them have something to
import. The port change and the two adapters follow, deterministic double last, because it
cannot speak from blocks until it is handed one.

## Critical Implementation Details

`Instruction.blocks` must stay a `tuple`. `frozen=True` on the model freezes field rebinding,
not the container behind the field — with a `Sequence` annotation pydantic stores a list and
`instruction.blocks.append(...)` succeeds on a validated instance, which would let a required
block be removed after the guard passed.

---

## Phase 1: Pin the shared instruction model

### Overview

The one module the contract session finished rather than stubbed. Its guards were probed
interactively in-session and never written down; this phase turns that probing into a suite.
Expect some assertions to pass on first run — that is the honest state of the module, and a
guard nobody can re-break silently is the deliverable.

### Changes Required:

#### 1. Shared instruction suite

**File**: `backend/tests/unit/shared/test_instruction_model.py`

**Intent**: Make every invariant `Instruction` and `InstructionBlock` claim in their
docstrings falsifiable, so a later edit that weakens one fails here rather than reaching a
model.

**Contract**: Exercises `InstructionBlock.rendered(name, template, **values)` — a template
whose placeholders exactly match the values renders and stores `text` alone; a missing key,
an unused value, and a positional `{}` each raise. Exercises `Instruction(blocks=…,
required=…)` — a missing required name raises, a repeated block name raises, a satisfied set
constructs, and `blocks` refuses post-construction mutation.

#### 2. Model corrections, if the suite finds any

**File**: `backend/src/domain/shared/instruction/model.py`

**Intent**: The suite is authored against the docstrings, not against the code. Where the two
disagree, the docstring is the contract and the code moves.

**Contract**: No signature change. `InstructionBlock`, `Instruction` and `InstructionBuilder`
keep their shape.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/shared/test_instruction_model.py -v`
- `cd backend && uv run pyright src/domain/shared/instruction`

---

## Phase 2: Coverage arithmetic and coverage policy

### Overview

The two derivations `coverage.py` declares and does not implement, plus the value objects
they read. Split deliberately: `trend_of` is arithmetic a test pins without anyone agreeing
on tone, `reading_of` is FR-03's judgement and is the part that gets revised after use.

### Changes Required:

#### 1. Trend and reading

**File**: `backend/src/domain/capture/coverage.py`

**Intent**: Turn the session's kept assessments into a direction, and the direction plus the
level into the single word the instruction speaks.

**Contract**: `trend_of(assessments) -> CoverageTrend` reads at most the last
`COVERAGE_TREND_WINDOW` entries and returns `FLAT` for fewer than two and for any movement
inside `COVERAGE_FLAT_BAND`. `reading_of(assessments) -> CoverageReading | None` returns
`None` only for an empty history; otherwise `WIDENING` on a falling trend, `DEEPENING` on a
rising one, and on a flat trend `SETTLED` at or above `COVERAGE_HIGH` and `EARLY` below it.

#### 2. Coverage suite

**File**: `backend/tests/unit/capture/test_coverage.py`

**Intent**: Pin the arithmetic separately from the policy, so revising the tone later does not
touch a test about numbers.

**Contract**: Covers the band (movement under it reads `FLAT`), the window (an old assessment
outside it does not decide the direction), the empty and single-assessment cases, and each of
the four readings. Includes a test that walks `CoverageReading` and asserts every member has
an entry in `_COVERAGE_READING_PROSE` — the exhaustiveness this repository recovers by test
(`context/foundation/rules/exceptions.md`).

#### 3. Value-object suite

**File**: `backend/tests/unit/capture/test_value_objects.py`

**Intent**: The float comes from the model, so its range is a guard and not a convention.

**Contract**: `Coverage` accepts the closed range and raises `CoverageOutOfRangeError` for a
value outside it, for `NaN`, and for an infinity.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/test_coverage.py tests/unit/capture/test_value_objects.py -v`

---

## Phase 3: Capture's phase builders build

### Overview

The composition the contract session made `@final` and the two `phase_blocks` it left empty.
This is where conditionality lives: a block the phase withholds is never rendered, and the
decision is taken over the set at once rather than per block.

### Changes Required:

#### 1. The final composition

**File**: `backend/src/domain/capture/instructions.py`

**Intent**: Compose the capture-wide floor with whatever the phase supplies, so the builder's
declared `required` and the instruction's carried `required` are the same value rather than
two that happen to agree.

**Contract**: `build(context)` returns `Instruction(blocks=(_FLOW, _LANGUAGE, *self.phase_blocks(context)), required=self.required)`.
General blocks lead; `required` stays `_GENERAL_REQUIRED | phase_required`.

#### 2. Conversing blocks

**File**: `backend/src/domain/capture/instructions.py`

**Intent**: Tell the agent what this turn of the conversation asks for, and carry FR-03's
reading as prose when there is one.

**Contract**: `phase_blocks` always yields `_CONVERSING_TASK`; yields a `SESSION_TOPIC` block
rendered from `_SESSION_TOPIC_TEMPLATE` iff `context.session.topic is not None`; yields a
`COVERAGE_TREND` block carrying `_COVERAGE_READING_PROSE[reading]` iff
`reading_of(context.session.assessments)` is not `None`. No block names a tool.

#### 3. Drafting blocks

**File**: `backend/src/domain/capture/instructions.py`

**Intent**: Say what state the note is in, because the empty case is the one that fails
(`DraftTopicMissingError`) when it is not told.

**Contract**: `phase_blocks` always yields `_DRAFTING_TASK` and exactly one `DRAFT_STATE`
block, selected three ways: `_DRAFT_STATE_EMPTY` when `context.draft is None` and
`context.session.note_id is None`; `_DRAFT_STATE_REVISING_TEMPLATE` when `context.draft is
None` and `context.session.note_id is not None`; `_DRAFT_STATE_UNDERWAY_TEMPLATE` when a
draft is in hand. Yields `_HANDOFF` iff `context.draft is None`.

#### 4. Builder suite

**File**: `backend/tests/unit/capture/test_capture_instructions.py`

**Intent**: Exercise the instruction with no model and no adapter in the loop, which is the
reason it lives in the domain at all.

**Contract**: Asserts block names and order per phase, each optional block's presence and
absence, that the general floor cannot be dropped, that `required` unions the floor, and that
a phase whose required block is withheld cannot construct an instruction.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/test_capture_instructions.py -v`
- `cd backend && uv run pyright src/domain/capture/instructions.py`

---

## Phase 4: Declare the wiring symbols

### Overview

Every symbol phases 5 and 6 need to import and nothing else. No behaviour: bodies stay
unimplemented, so nothing here can be asserted and this phase carries no tests.

### Changes Required:

#### 1. Instruction hook on the graph

**File**: `backend/src/domain/shared/graph/model.py`

**Intent**: Give a phase somewhere to declare its builder, mirroring how it declares its tool
inventory.

**Contract**: `State` gains an abstract property `instruction_builder -> InstructionBuilder[ContextT]`.
Abstract on purpose: a phase that reaches a model without saying what it tells it is the case
this change exists to prevent.

**File**: `backend/src/domain/shared/graph/machine.py`

**Contract**: `StateMachine.build_instruction(self) -> Instruction`, unimplemented, sitting
beside `get_tools`.

#### 2. Coverage crosses into the domain

**File**: `backend/src/domain/capture/graph.py`

**Intent**: Free the name `CoverageAssessed` for the event, and guard the model's float where
it enters.

**Contract**: The `ToolResult` is renamed `CoverageAssessment` and its field becomes
`coverage: Coverage`; `tool` stays `"assess_coverage"` so the discriminator still matches.
A module-level `async def _record_coverage_assessment(context, deps, event) -> None` is
declared unimplemented and added to `Conversing.actions`.

**File**: `backend/src/domain/capture/turn.py`

**Contract**: A new `CoverageAssessed(BaseModel, frozen=True)` with
`kind: Literal["coverage_assessed"]` and `coverage: Coverage`, added to the `AgentEvent`
union.

#### 3. The instruction crosses the port

**File**: `backend/src/domain/capture/ports.py`

**Intent**: The instruction reaches the adapter the same way the tools do — already decided by
the phase, with nothing left for the adapter to infer.

**Contract**: `CaptureAgentPort.converse(turn, tools, instruction)` takes a third positional
parameter `instruction: Instruction`. Both adapter signatures are widened to match, and the
parameter is accepted and unused until phases 6 and 7.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pyright src`

---

## Phase 5: The session keeps what the model assessed

### Overview

Coverage stops being telemetry the adapter writes onto the turn and becomes an event the
machine applies and the aggregate keeps. The float still leaves on `ReplyDoneEvent`; it is now
read from the session.

### Changes Required:

#### 1. Recording action

**File**: `backend/src/domain/capture/graph.py`

**Intent**: Route the event to the aggregate by the same path the phase and the consent
already take, so a later event-sourced reading of the session inherits it for free.

**Contract**: `_record_coverage_assessment` calls `context.session.record_assessment(event.coverage)`
on a `CoverageAssessed` and does nothing otherwise; `Conversing.get_actions` selects it on
`isinstance(event, CoverageAssessed)`. `_assess_coverage` builds
`CoverageAssessment(coverage=Coverage(value=_require_float(arguments, "coverage")))` — an
out-of-range value raises `CoverageOutOfRangeError` from the handler and fails the turn.

#### 2. Provider adapter maps the result

**File**: `backend/src/adapters/out/llm/capture/agent.py`

**Contract**: `_event_from_tool_result` maps `CoverageAssessment` to
`CoverageAssessed(coverage=result.coverage)`.

#### 3. The float's source moves

**File**: `backend/src/domain/capture/turn.py`

**Intent**: Two copies of one fact that nothing keeps in agreement become one.

**Contract**: `CaptureTurn.coverage_confidence` is removed.

**File**: `backend/src/application/capture/commands/send_message.py`

**Contract**: `ReplyDoneEvent.coverage_confidence` reads `session.assessments[-1].value`, or
`0.0` when the session holds none. The DTO field and the HTTP/TUI contract are unchanged.

**File**: `backend/src/adapters/out/in_memory/capture/capture_agent.py`

**Contract**: The double stops writing `turn.coverage_confidence` and yields
`CoverageAssessed` when `assess_coverage` is among the tools it was handed.

#### 4. Acceptance step follows

**File**: `backend/tests/bdd/steps/coverage_wrapup.py`

**Contract**: `_FullCoverageCaptureAgent` yields a `CoverageAssessed(coverage=Coverage(value=1.0))`
instead of setting a field on the turn. The feature file and its assertions are untouched.

#### 5. Suites

**File**: `backend/tests/unit/capture/test_capture_graph.py`, `backend/tests/unit/capture/test_send_message_command.py`

**Intent**: Pin that the assessment survives the turn, which is what FR-03 rests on.

**Contract**: Applying `CoverageAssessed` appends to `session.assessments` and appends again
rather than overwriting; a tool argument outside `[0, 1]` raises `CoverageOutOfRangeError`;
`ReplyDoneEvent.coverage_confidence` reflects the session's last assessment and is `0.0` for a
session with none.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture tests/bdd -v`

#### Manual Verification:
- `cd backend && uv run pytest` — the full suite, since the rename reaches existing capture tests.

---

## Phase 6: The machine hands the instruction across the port

### Overview

The `if` on the phase leaves the adapter. The machine asks the current phase for its
instruction, the command passes it with the tools, and the provider adapter renders the blocks
as the sequence pydantic-ai already accepts.

### Changes Required:

#### 1. Phases declare their builders

**File**: `backend/src/domain/capture/graph.py`

**Contract**: `Conversing.instruction_builder` returns a `ConversingInstructionBuilder`,
`Drafting.instruction_builder` a `DraftingInstructionBuilder`.

**File**: `backend/src/domain/shared/graph/machine.py`

**Contract**: `build_instruction()` returns `self.current_state.instruction_builder.build(self._context)`.

#### 2. Fake states follow the abstraction

**File**: `backend/tests/unit/shared/test_graph_model.py`, `backend/tests/unit/shared/test_graph_machine.py`, `backend/tests/property/shared/test_graph_model_properties.py`, `backend/tests/property/shared/test_graph_machine_properties.py`

**Intent**: An abstract member is a promise every implementation keeps, including the ones
that exist only to exercise the graph.

**Contract**: Each of the 11 fake `State` subclasses declares an `instruction_builder`
returning a minimal builder over its own context type.

#### 3. The command passes it

**File**: `backend/src/application/capture/commands/send_message.py`

**Contract**: `_open_stream` calls
`self._capture_agent.converse(turn, machine.get_tools(), machine.build_instruction())`.
The machine is still handed no port and consumes no stream.

#### 4. The provider adapter renders blocks

**File**: `backend/src/adapters/out/llm/capture/agent.py`

**Intent**: The adapter's whole remaining job with prose is to carry it, so block boundaries
survive rather than being flattened by a separator the domain never authorised.

**Contract**: `converse` passes `instructions=[block.text for block in instruction.blocks]`.
`_instructions_for`, `_CONVERSING_INSTRUCTIONS` and `_DRAFTING_INSTRUCTIONS` are deleted.

#### 5. Contract suite carries the third argument

**File**: `backend/tests/unit/capture/contracts/test_capture_agent_contract.py`

**Contract**: Every `converse` call passes an instruction built by the turn's phase; the
suite still runs over both implementations.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit -v`
- `cd backend && uv run pyright src`
- `cd backend && grep -rn "_CONVERSING_INSTRUCTIONS\|_DRAFTING_INSTRUCTIONS\|_instructions_for" src` — expect no matches.

#### Manual Verification:
- Run a capture session end to end and confirm the reply still streams and the session still
  drafts on the user's word.

---

## Phase 7: The deterministic double speaks from blocks

### Overview

The double is an adapter that renders an instruction, not an exception to the rule. What stays
with it is how a fake agent fakes being one: chunking, pacing, and the fixed phrase list by
which it simulates reading consent — an impersonation mechanic, never domain policy.

### Changes Required:

#### 1. Prose leaves the double

**File**: `backend/src/adapters/out/in_memory/capture/capture_agent.py`

**Intent**: Where it had a line to say, it now says the block's.

**Contract**: `_HANDOFF_LINE`, `_DEFAULT_SOLID` and `_DEFAULT_SHAKY` are deleted. The drafting
opener is the `HANDOFF` block's text; the conversational reply is composed from the texts of
the blocks it was handed. `_conversational_reply` takes the instruction rather than a
`ConfidenceAssessment`.

#### 2. Blocks decide the branch

**File**: `backend/src/adapters/out/in_memory/capture/capture_agent.py`

**Intent**: Nothing in the adapter infers its phase. The instruction it is handed is already
the current phase's, so reading the tool set to work out where it is is the mode machine of
its own the effort forbids — and with no model, block presence is the only signal left that
the domain authored.

**Contract**: The drafting branch is selected by the presence of the `DRAFT_STATE` block
rather than by `_NOTE_TOOL_NAMES.issubset(tools_by_name)`; `_NOTE_TOOL_NAMES` is deleted. The
consent branch still requires `signal_drafting_consent` among the tools, because consent is a
capability and capability is the tool channel's to say.

#### 3. Double suite

**File**: `backend/tests/unit/capture/test_deterministic_capture_agent.py`

**Contract**: The existing three tests pass an instruction; new assertions pin that the
drafting opener is the `HANDOFF` block's text verbatim, that the reply contains no string the
adapter authored, and that the branch follows the instruction's blocks rather than the tools.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest -v`
- `cd backend && grep -rn "_HANDOFF_LINE\|_DEFAULT_SOLID\|_DEFAULT_SHAKY\|_NOTE_TOOL_NAMES" src` — expect no matches.

#### Manual Verification:
- Run a capture session against the in-memory composition and read the reply: every sentence
  should be traceable to a block in `backend/src/domain/capture/instructions.py`.

---

## Testing Strategy

### Unit Tests:

New suites for the shared instruction model, capture's coverage derivations, and both phase
builders — none of which needs a model, an adapter, or a session store. Existing capture graph
and command suites extend to cover the assessment's survival on the aggregate.

### Integration Tests:

The `CaptureAgentPort` contract suite runs the widened signature over both implementations.
The BDD coverage wrap-up feature is unchanged; only its step's mechanism moves from a turn
field to an event.

### Manual Testing Steps:

1. `cd backend && uv run pytest`
2. Run a capture session end to end; confirm reply streaming, the drafting handoff line, and
   that `done` still carries a coverage figure.

## Performance Considerations

Building an instruction is synchronous and reaches no port — it reads only what the turn
already holds in memory. `trend_of` looks at a bounded window, so the cost does not grow with
a long session's assessment history.

## Migration Notes

No schema or persistence change. `CaptureSession.assessments` defaults to `()`, so a session
stored before this change loads with an empty history and reads as having no coverage
reading — correct, not a special case. The HTTP and TUI contracts are untouched.

## References

- `context/changes/llm-adapter-instruction-context/frame.md`
- `context/changes/llm-adapter-instruction-context/discover-contracts-log.md` — later
  authority where it and the frame disagree
- `context/efforts/llm-adapter/frame.md` — FR-03, FR-05, FR-09
- `context/efforts/llm-adapter/roadmap.md` — slice S-03
- `context/foundation/testing-conventions.md`
- `context/foundation/rules/exceptions.md`

## Execution state

Tracked in `todos.md`, sibling of this file.
