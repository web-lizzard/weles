# Capture Instruction Context — Plan Brief

> Full plan: `plan.md`

## What & Why

Capture's model-facing prose becomes a domain artifact: each phase builds an `Instruction` —
an ordered tuple of named blocks with a declared required set — from the turn it already
holds, and hands it across the agent port beside the tools. Adapters render what they are
given and author nothing. Assessed coverage reaches the domain as an event, survives on the
session, and comes back out as a word rather than the float the model sent (FR-03, FR-05).

## Starting Point

The contract-shaping session put the types, the builder hierarchy and all the prose on disk
in `dd41b36`, with four bodies deliberately empty and no tests. Nothing consumes an
instruction yet: the provider adapter picks between two module constants with an `if` on the
phase, and the deterministic double holds its own lines and infers its phase from the tool
set it was handed.

## Desired End State

A capture turn dispatches an instruction the domain built. No prose constant remains in
either adapter, an instruction missing a required block cannot be constructed, and the
session keeps every coverage assessment so a later turn's instruction can be built from the
trend. The HTTP and TUI contracts do not move.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Where a phase declares its builder | Abstract `instruction_builder` on shared `State`, with `StateMachine.build_instruction` beside `get_tools` | Exact mirror of the tool inventory, so every graph inherits the hook and distill gets it for free. | Plan |
| How the instruction crosses the port | Third parameter on `converse(turn, tools, instruction)` | Symmetric with `tools` — both are things the phase decided for this turn. | Plan |
| `CaptureTurn.coverage_confidence` | Removed; `ReplyDoneEvent` reads the session's last assessment | Two copies of one fact with nothing holding them in agreement. | Contracts |
| Where the `[0,1]` guard fires | `CoverageAssessment.coverage` typed `Coverage` | A NaN or a 7.3 dies where it enters, not after it has reached the session. | Plan |
| FR-05 failure type | Stays `ValueError` | Broken by an author in a test, not by a user at runtime. | Plan |
| Provider rendering | `instructions=[block.text, …]` | pydantic-ai 2.35.3 accepts a sequence, so block boundaries survive with no separator the adapter invented. | Plan |
| Deterministic double | Speaks the blocks, and branches on block presence | With no model, block presence is the only signal the domain authored; reading the tool set would be the mode machine of its own the effort forbids. | Frame |
| Coverage and capability | Coverage shapes tone, never capability | Prose cannot withdraw a tool the provider already showed; supersedes one sentence of `frame.md`. | Contracts |

## Scope

**In scope:** `domain/shared/instruction/`, `domain/shared/graph/`, `domain/capture/`
(instructions, coverage, graph, turn, ports), `send_message`, both capture agent adapters,
and the suites that follow them.

**Out of scope:** provider-facing tool definitions (S-04), distill's instructions, any
evaluation of output quality, a domain exception for the FR-05 guard, and any change to the
HTTP or TUI contract.

## Architecture / Approach

Bottom-up. The two pure surfaces left unimplemented come first — coverage arithmetic, then
the builders that read it — each pinned by unit tests with no model and no adapter in the
loop, which is the argument for placing them in the domain at all. One stubs phase then
declares every wiring symbol that does not exist yet, so the behaviour phases above it have
something to import. Port and provider adapter follow; the deterministic double is last,
because it cannot speak from blocks until it is handed one.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Pin the shared instruction model | A suite over `InstructionBlock` and `Instruction` guards | The module is already implemented, so parts of the suite go green on first run |
| 2. Coverage arithmetic and policy | `trend_of`, `reading_of`, and the value-object guards | Band and window thresholds are domain judgements, easy to pin too tightly |
| 3. Capture's phase builders build | `build` plus both `phase_blocks`, with their conditionality | Requiredness is static; a block made conditional here would make FR-05's guard a tautology |
| 4. Declare the wiring symbols | State hook, machine method, port parameter, `CoverageAssessed` event, `CoverageAssessment` rename | The rename reaches existing capture tests |
| 5. The session keeps what the model assessed | Recording action, adapter mapping, `coverage_confidence` moved to the session | A BDD step exists only to write the field being removed |
| 6. The machine hands the instruction across the port | Builders on both phases, command passes it, provider renders blocks | An abstract `instruction_builder` touches 11 fake states across unit and property suites |
| 7. The deterministic double speaks from blocks | Adapter prose deleted, branch keyed on block presence | Its reply changes shape, so three existing assertions move |

**Prerequisites:** S-02 (done). Ordering inside the change: 2 → 3, 4 → 5, 4 → 6, 6 → 7.
**Estimated effort:** 7 phases; phases 5 and 6 carry the migration weight.

## Open Risks & Assumptions

- The abstraction is shaped by capture alone. Distill has no graph, no agent port and no live
  adapter until S-06, and that is the risk `frame.md` accepts rather than mitigates.
- A reader who opens `frame.md` and not `discover-contracts-log.md` will believe the
  superseded sentence about low coverage removing the consent option. No test may assert it.
- `CoverageOutOfRangeError` raised from the tool handler fails the turn rather than dropping
  the assessment. The 422 mapping already exists; the loud failure is deliberate.

## Success Criteria (Summary)

- `cd backend && uv run pytest` green, with new suites for the instruction model, coverage,
  and both builders.
- No prose constant left in either capture adapter.
- A capture session still replies, still drafts on the user's word, and still reports a
  coverage figure on `done` — now read from the session.
