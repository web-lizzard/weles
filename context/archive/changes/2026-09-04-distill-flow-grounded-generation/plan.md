# Grounded Flashcard Generation Implementation Plan

## Overview

Slice S-02 of the `distill-flow` effort. Today an approved note lands in distill as a `Note` in `generating` status and enqueues a `note_saved` envelope that nothing consumes. This plan builds the entire card side of the distill domain — the `Card` aggregate, its value objects, the `CardFactory` and its policies, the generation and parser ports with their in-memory adapters, the `GenerateCardsCommand`, and the `FlashcardGenHandler` that consumes `note_saved` — so that cards come into existence with no user action, every live card quotes its note verbatim, and a note yielding zero live cards is reported as completed rather than failed.

Realizes AC-03, AC-04, AC-05, AC-06 (US-02, US-03) and FR-002 through FR-006.

## Current State Analysis

The distill bounded context implements only the note-save half of the ADR's two-handler outbox chain:

- `Note` aggregate — a passive snapshot with embedded `TopicSnapshot` / `TagSnapshot`, sharing capture's `NoteId`, always minted in `generating` (`backend/src/domain/distill/note.py:15-43`). Only `generating` is ever written.
- Note value objects — `NoteId`, `SessionId`, `NoteContent`, `DistillationStatus` (`backend/src/domain/distill/value_objects.py:14-54`).
- `NoteRepository` — `add` / `get` (`backend/src/domain/distill/ports.py:7-10`).
- `SaveNoteCommand` — idempotent on `note_id`, persists and enqueues `note_saved` (`backend/src/application/distill/commands/save_note.py`).
- `SaveNoteHandler` — consumes `note_approved`, delegates to the command (`backend/src/adapters/out/worker/handlers/note_save.py`).
- `UnitOfWork` — `notes` + `outbox` only (`backend/src/application/distill/ports.py:7-15`).

Nothing card-shaped exists: no `Card`, `CardRepository`, `CardFactory`, `CardGeneration`, `NoteDocumentParser`, or `FlashcardGenHandler`. `compose.py` registers `SaveNoteHandler` as the only outbox handler (`backend/src/adapters/compose.py:119-127`).

Key constraints discovered while planning:

- `OutboxWorker.run_once()` claims per handler **sequentially in list order** (`backend/src/adapters/out/worker/outbox_worker.py:29-31`), so registering `FlashcardGenHandler` after `SaveNoteHandler` lets one pass drain the whole chain — `note_saved` is appended before the second handler's claim runs.
- `EXCEPTION_STATUS_MAP` (`backend/src/adapters/http/errors.py:6-36`) is closed by a recursive subclass-walking exhaustiveness test, so every new `CoreException` owes an entry regardless of whether any HTTP route can reach it. S-01 hit this mid-phase.
- The `distill-flow` marker is **not** registered in `backend/pyproject.toml:37-53`; only `capture-flow` and `AC-01`…`AC-15` are. AC numbers collide across efforts, so the effort tag is what disambiguates a `-m` filter.
- `tests/integration/support/` holds only `in_memory_capture.py`. Acceptance scenarios reaching distill need their own composition sharing capture's `outbox_store`.
- distill's `NoteRepository.add` is already contractually an upsert — `test_second_add_with_same_id_overwrites` (`backend/tests/unit/distill/contracts/test_note_repository_contract.py:64-78`) pins it.

## Desired End State

A note approved in capture produces, with no further user action, a set of live cards each carrying a verbatim quote resolvable within that note's content, plus persisted discarded rows for every proposal whose quote did not resolve or whose sides breached the configured length policy. The note's `distillation_status` reaches `ready` whether it produced ten live cards or none, and reaches `failed` only when the generation port itself fails.

Verified by: `cd backend && uv run pytest` green, including two new acceptance features under `tests/features/distill-flow/`, and a manual outbox drain showing `note_saved` reaching `consumed`.

### Key Discoveries:

- `CaptureSessionRepository.save` (`backend/src/domain/capture/ports.py:15`) is the in-repo precedent for a repeatedly-mutated aggregate's port method; `add` is used for write-once aggregates. Distill's `Note` becomes the former in this slice.
- `MatchCriteria` (`backend/src/domain/capture/vocabulary.py:15-34`) is the precedent for a frozen domain value object that carries a judgement method — the shape `CardLengthPolicy` follows.
- Every meaningful string in `domain/capture/value_objects.py` is a frozen `BaseModel` that strips on input and raises its own `CoreException`; `NoteContent` (`backend/src/domain/distill/value_objects.py:32-48`) already mirrors it in distill.
- S-01 set the precedent of naming only what the slice calls: its plan-brief declined to add `UnitOfWork.cards` as an unused stub. This plan applies the same rule to `NoteDocumentParser`.
- `mint_note` (`backend/src/domain/distill/note.py:26-43`) establishes module-level construction rather than a classmethod.
- The deterministic in-memory adapters for capture's algorithmic seams (`reply_generation`, `topic_extraction`, `confidence_assessment`) are the model for `CardGeneration`'s in-memory implementation.

## What We're NOT Doing

- No `DiscardCard` command and no caller for `DiscardReason.user_audit` — the value stays in the enum per the ADR, with nothing setting it (PRD Non-Goals bars manual curation).
- No query DTOs, note list, or note detail (S-03, S-04); no anchor-jump surface (S-05).
- No `NoteDocumentParser.blocks` method — rendering needs it, and rendering is S-04.
- No `cards_generated` envelope; remember wraps cards lazily.
- No regeneration, no timeout, and no sweeper for a note stranded in `generating`.
- No surface for inspecting discarded rows — they are persisted (FR-006) and unread.
- No scheduling state of any kind on `Card`.
- No SQL or LLM adapters; InMemoryFirst holds.

## Implementation Approach

The chain the ADR specifies is `note_approved → [note-save] → note_saved → [flashcard-gen]`. S-01 built the first handler; this plan builds the second and everything it needs.

The grounding invariant splits across two layers exactly as the ADR requires: the **application** resolves each proposal's quote through the `NoteDocumentParser` port, and the **domain** judges what was resolved. `CardFactory.mint` therefore takes an already-resolved verdict and returns a `Card` that is either live (`discard is None`) or discarded — never `None`, and never a raw proposal.

Evaluation order inside the factory is fixed and load-bearing: grounding first (it is the domain's one non-negotiable invariant and deliberately sits outside the configurable policy collection), then `CardLengthPolicy`, first violation wins. A structurally invalid proposal — empty side, past the absolute `CardSide` bound, or two identical sides — raises out of construction before any discard verdict is reached; the command catches it per proposal, logs, and continues, so one malformed proposal cannot cost the user the rest of the run.

Work is sequenced domain-outward: value objects, then the aggregate and its factory, then ports and their in-memory adapters, then the application command, then the outbox handler, then composition, then acceptance scenarios. Each TDD'able unit is split into a stubs phase that materializes symbols and a behavior phase that implements and tests them.

## Critical Implementation Details

`Card.anchor` is non-optional and holds the **claimed** quote whether or not it resolved — a discarded-`ungrounded` card still carries the quote the generator cited, which is the whole point of persisting the row. Resolution is therefore expressed as a separate `AnchorResolution` verdict passed into the factory, not as `Anchor | None`.

Handler registration order in `compose.py` is semantic, not cosmetic: `SaveNoteHandler` must precede `FlashcardGenHandler` in the `OutboxWorker` list or a single `run_once()` will not drain the chain, and every acceptance scenario drains with one call.

---

## Phase 1: Card value objects and exceptions — stubs

### Overview

Materialize every card-side value object and exception as importable symbols with fields and signatures only, so Phase 2's tests have something to import.

### Changes Required:

#### 1. Card exceptions

**File**: `backend/src/domain/distill/exceptions.py`

**Intent**: Give the card-side construction failures and the illegal status transition their own `CoreException` subclasses, so each derives a wire-visible `code`.

**Contract**: Adds `EmptyCardSideError`, `CardSideTooLongError`, `EmptyAnchorError`, `IdenticalCardSidesError`, `InvalidDistillationTransitionError`, all `CoreException` subclasses with `pass` bodies. Unlike S-01's note-content exceptions these need no `Distill` prefix — no capture exception collides on the derived codes `empty_card_side`, `card_side_too_long`, `empty_anchor`, `identical_card_sides`, `invalid_distillation_transition`.

#### 2. Card value objects

**File**: `backend/src/domain/distill/value_objects.py`

**Intent**: Add the card-side vocabulary alongside the existing note vocabulary, following the frozen-`BaseModel`-with-`value` convention the module already uses.

**Contract**: Adds module constants `CARD_SIDE_MAX_LENGTH`, `ANCHOR_MAX_LENGTH`; `CardId(value: UUID)`; `CardSide(value: str)`; `Anchor(quote: str)`; `DiscardReason(StrEnum)` with `UNGROUNDED`, `OVERSIZED`, `USER_AUDIT`; `AnchorResolution(StrEnum)` with `RESOLVED`, `UNRESOLVED`; `Discard(reason: DiscardReason, detail: str | None, discarded_at: datetime)`; `CardLengthPolicy(front_max: int, back_max: int)` with an unimplemented `breach(front: CardSide, back: CardSide) -> str | None`. All frozen. No validators yet.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run ruff check src` clean
- `cd backend && uv run basedpyright` clean
- Every new symbol imports from `domain.distill.value_objects` and `domain.distill.exceptions`

#### Manual Verification:
- `cd backend && uv run python -c "from domain.distill.value_objects import CardSide, Anchor, Discard, DiscardReason, AnchorResolution, CardLengthPolicy, CardId; print('ok')"`

---

## Phase 2: Card value objects and exceptions — behavior

### Overview

Implement the construction invariants and the length-policy judgement, and prove them.

### Changes Required:

#### 1. `CardSide` and `Anchor` validation

**File**: `backend/src/domain/distill/value_objects.py`

**Intent**: Make each side and each anchor canonicalize and validate itself, so no bare string carrying these meanings exists in the domain.

**Contract**: `CardSide` strips on input, raises `EmptyCardSideError` when empty and `CardSideTooLongError` past `CARD_SIDE_MAX_LENGTH`. `Anchor` strips its `quote`, raises `EmptyAnchorError` when empty and `CardSideTooLongError`'s anchor counterpart past `ANCHOR_MAX_LENGTH`. The empty-anchor rule closes a real hazard: an empty quote is a substring of every note, so without it a fabricated proposal with a blank citation would resolve as grounded.

#### 2. `CardLengthPolicy.breach`

**File**: `backend/src/domain/distill/value_objects.py`

**Intent**: State the front/back asymmetry in the one place it varies, and return a `detail` string that names which side and which bound was breached — without it a discard rate has no referent across policy changes.

**Contract**: `breach(front, back) -> str | None` checks `front` against `front_max` first, then `back` against `back_max`, returning the first breach as `"front exceeds front_max=<n>"` / `"back exceeds back_max=<n>"`, or `None` when neither breaches. First-violation-wins ordering lives here.

#### 3. Value-object tests

**File**: `backend/tests/unit/distill/test_card_value_objects.py`

**Intent**: Pin every construction rule and the policy's ordering.

**Contract**: Covers strip-on-input, empty rejection and bound rejection for `CardSide` and `Anchor`; `breach` returning `None`, the front detail, the back detail, and the front-wins-when-both-breach case.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/test_card_value_objects.py` green
- `cd backend && uv run pytest` green (requires the five new codes in `EXCEPTION_STATUS_MAP`; see Phase 13 — add them here if the exhaustiveness test fails first)
- `cd backend && uv run ruff check src tests` clean

#### Manual Verification:
- `cd backend && uv run pytest tests/unit/distill -v` and read the test names as a statement of the card-side rules

---

## Phase 3: Card aggregate and CardFactory — stubs

### Overview

Materialize the `Card` aggregate and the single minting door, signatures only.

### Changes Required:

#### 1. `Card` aggregate

**File**: `backend/src/domain/distill/card.py`

**Intent**: Hold the two-sided artifact, its anchor into the note, and its whole removal state in one non-frozen `BaseModel`.

**Contract**: `Card(BaseModel)` with `id: CardId`, `note_id: NoteId`, `front: CardSide`, `back: CardSide`, `anchor: Anchor`, `discard: Discard | None`, `created_at: datetime`. A `model_validator(mode="after")` named `_validate_sides_differ` is declared with an unimplemented body. No status field — `discard is None` is the live predicate.

#### 2. `CardFactory`

**File**: `backend/src/domain/distill/card_factory.py`

**Intent**: Make one object the only door a proposal passes through, constructed once at composition with its policy, so no call site threads a policy and a second policy joins later without touching `Card` or any handler.

**Contract**:

```python
class CardFactory:
    def __init__(self, length_policy: CardLengthPolicy) -> None: ...

    def mint(
        self,
        note_id: NoteId,
        front: CardSide,
        back: CardSide,
        anchor: Anchor,
        resolution: AnchorResolution,
    ) -> Card: ...
```

`mint` returns a `Card` in every case — live or discarded — and never `None`. `resolution` is the verdict the application obtained from the parser; the domain judges it rather than reaching for the parser itself.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run ruff check src` and `uv run basedpyright` clean
- `Card` and `CardFactory` import from their modules

#### Manual Verification:
- `cd backend && uv run python -c "from domain.distill.card_factory import CardFactory; print(CardFactory.mint.__annotations__)"`

---

## Phase 4: Card aggregate and CardFactory — behavior

### Overview

Implement the aggregate's one invariant and the factory's fixed evaluation order, and prove both.

### Changes Required:

#### 1. Differing-sides invariant

**File**: `backend/src/domain/distill/card.py`

**Intent**: Enforce the only rule `Card` can hold on its own; grounding it cannot, because that needs the parser.

**Contract**: `_validate_sides_differ` raises `IdenticalCardSidesError` when `front.value.casefold() == back.value.casefold()`. `CardSide` has already stripped, so casefold is the whole of the canonicalization — anything cleverer is a similarity judgement and belongs to the generator.

#### 2. Factory evaluation order

**File**: `backend/src/domain/distill/card_factory.py`

**Intent**: Make minting deterministic and put grounding outside the configurable collection, so a fabricated card is reported as fabricated even when it is also verbose.

**Contract**: `mint` constructs the `Card` first (so a structurally invalid proposal raises before any discard verdict), then: `resolution is UNRESOLVED` → `Discard(reason=UNGROUNDED, detail=None)`; else `length_policy.breach(front, back)` non-`None` → `Discard(reason=OVERSIZED, detail=<breach string>)`; else `discard=None`. `discarded_at` is stamped `datetime.now(UTC)`. One `Discard` per card — the first violation wins.

#### 3. Aggregate and factory tests

**File**: `backend/tests/unit/distill/test_card.py`, `backend/tests/unit/distill/test_card_factory.py`

**Intent**: Pin the invariant, the ordering, and the fact that a discarded proposal still becomes a persisted card.

**Contract**: Covers identical sides (including case-insensitive) raising; a live card carrying `discard is None`; an unresolved anchor minting `Discard(ungrounded)` while retaining the claimed quote in `anchor`; an oversized side minting `Discard(oversized)` with a `detail` naming the side; and the ordering case where a proposal is both unresolved and oversized minting `ungrounded`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/test_card.py tests/unit/distill/test_card_factory.py` green
- `cd backend && uv run pytest` green

#### Manual Verification:
- `cd backend && uv run pytest tests/unit/distill/test_card_factory.py -v` and confirm the ordering test name states grounding-before-length

### Review r2

Artifact: `reviews/2026-09-05-r2-mutation-test-phases-2-4-8-.md`

- `R2-F3` — mint must stamp created_at in UTC
  Fix: assert every minted `Card.created_at.tzinfo is UTC`, including live cards
- `R2-F4` — oversized discard must stamp discarded_at in UTC
  Fix: assert an oversized mint sets `card.discard.discarded_at.tzinfo is UTC`

---

## Phase 5: Note transitions and repository ports — stubs

### Overview

Materialize the note's status transitions, the renamed note repository method, and the card repository with its in-memory skeleton.

### Changes Required:

#### 1. `Note` transitions

**File**: `backend/src/domain/distill/note.py`

**Intent**: Put the `generating → ready | failed` state machine on the aggregate that owns the field, so no caller can reach the status by assignment.

**Contract**: Adds `mark_ready() -> None` and `mark_failed() -> None` as mutating methods with unimplemented bodies, plus a private `_ensure_generating() -> None` declared last per the code-ordering rule.

#### 2. `NoteRepository.save` and `CardRepository`

**File**: `backend/src/domain/distill/ports.py`

**Intent**: Name the note port's method for what the contract already proves it does, and add the card port.

**Contract**: `NoteRepository.add` is **renamed to** `save(note: Note) -> None`; `get` unchanged. `CardRepository` is added with `save(card: Card) -> None` and `list_by_note(note_id: NoteId) -> list[Card]`. Both ports use `save`, so distill has one repository verb.

#### 3. Call-site and adapter rename

**File**: `backend/src/application/distill/commands/save_note.py`, `backend/src/adapters/out/in_memory/distill/note_repository.py`

**Intent**: Carry the rename through the one call site and the one adapter.

**Contract**: `uow.notes.add(note)` becomes `uow.notes.save(note)` (`save_note.py:39`); `InMemoryNoteRepository.add` becomes `save` with its body unchanged. `snapshot` / `restore` untouched.

#### 4. `InMemoryCardRepository` skeleton

**File**: `backend/src/adapters/out/in_memory/distill/card_repository.py`

**Intent**: Give the card port an in-memory implementation before any I/O-bound one, per InMemoryFirst.

**Contract**: `InMemoryCardRepository` with unimplemented `save`, `list_by_note`, `snapshot() -> dict[UUID, Card]`, `restore(snapshot) -> None`, mirroring `InMemoryNoteRepository`'s shape so the `UnitOfWork` can snapshot it.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run ruff check src` and `uv run basedpyright` clean
- `cd backend && uv run pytest tests/unit/distill/test_save_note_command.py` still green after the rename

#### Manual Verification:
- `cd backend && uv run grep -rn "notes.add\|\.add(note" src` returns nothing

---

## Phase 6: Note transitions and repository ports — behavior

### Overview

Implement the guarded transitions and both in-memory repositories, and rewrite the note contract suite around `save`.

### Changes Required:

#### 1. Guarded transitions

**File**: `backend/src/domain/distill/note.py`

**Intent**: Defend the state machine where it lives, so a delivery that slips past the command's idempotency check still cannot rewrite a finished note.

**Contract**: `_ensure_generating` raises `InvalidDistillationTransitionError` when `distillation_status is not DistillationStatus.GENERATING`; `mark_ready` and `mark_failed` call it before assigning `READY` / `FAILED`. The aggregate gains no other guard — its content stays mutable, per the ADR's refusal of capture's `_ensure_draft` mirror.

#### 2. `InMemoryCardRepository`

**File**: `backend/src/adapters/out/in_memory/distill/card_repository.py`

**Intent**: Store cards keyed by card id with a note-id lookup, deep-copying on snapshot so the `UnitOfWork` can roll back.

**Contract**: `save` upserts by `card.id.value`; `list_by_note` returns every card whose `note_id` matches, **discarded rows included** — filtering live cards is the caller's job, which is the cost the ADR accepted for one relation.

#### 3. Contract suites

**File**: `backend/tests/unit/distill/contracts/test_note_repository_contract.py`, `backend/tests/unit/distill/contracts/test_card_repository_contract.py`

**Intent**: One behavioral contract per port, parametrized over implementations.

**Contract**: The note suite's three cases are renamed to `save` (`test_save_then_get_returns_the_saved_note`, `test_get_returns_none_for_unknown_note_id`, `test_second_save_with_same_id_overwrites`). The card suite covers save-then-list, an unknown note id returning `[]`, discarded cards appearing in `list_by_note`, and a second save with the same id overwriting.

#### 4. Transition tests

**File**: `backend/tests/unit/distill/test_note.py`

**Intent**: Pin both legal transitions and the guard.

**Contract**: Extends the existing module with `mark_ready` and `mark_failed` from `generating`, and both raising `InvalidDistillationTransitionError` from `ready` and from `failed`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill` green
- `cd backend && uv run pytest` green

#### Manual Verification:
- `cd backend && uv run pytest tests/unit/distill/contracts -v` and confirm both suites report the `in_memory` parametrization id

---

## Phase 7: Application ports and outbound adapters — stubs

### Overview

Materialize the application-layer proposal type, the two outbound ports, the extended `UnitOfWork`, and both adapter skeletons. This one stubs phase precedes Phases 8 and 9.

### Changes Required:

#### 1. `CardProposal`

**File**: `backend/src/application/distill/value_objects.py`

**Intent**: Carry what the generation port produces, in raw strings, so the command is the layer that builds domain value objects and therefore the layer that catches their construction failures.

**Contract**: New module mirroring `application/capture/value_objects.py`. `CardProposal(BaseModel, frozen=True)` with `front: str`, `back: str`, `quote: str`.

#### 2. Outbound ports and `UnitOfWork.cards`

**File**: `backend/src/application/distill/ports.py`

**Intent**: Name distill's algorithmic seam and its parsing seam, and give the unit of work the card repository.

**Contract**: Adds `CardGeneration` with `async generate(content: NoteContent) -> list[CardProposal]`; `NoteDocumentParser` with `async resolves(content: NoteContent, quote: str) -> bool`. The parser gets **no `blocks` method** — the ADR's port includes one for rendering, and rendering is S-04; S-01 set the precedent of naming only what the slice calls. `UnitOfWork` gains `cards: CardRepository`.

#### 3. `InMemoryUnitOfWork` cards

**File**: `backend/src/adapters/out/in_memory/distill/unit_of_work.py`

**Intent**: Bring cards under the same snapshot/restore rollback the notes and outbox already get.

**Contract**: Constructor takes `cards: InMemoryCardRepository`; `__aenter__` snapshots it; `__aexit__` restores it when `commit` was never called.

#### 4. Adapter skeletons

**File**: `backend/src/adapters/out/in_memory/distill/note_document_parser.py`, `backend/src/adapters/out/in_memory/distill/card_generation.py`

**Intent**: Give both seams in-memory implementations before any model-backed one.

**Contract**: `MarkdownNoteDocumentParser` with an unimplemented `resolves`; `DeterministicCardGenerationAdapter` with an unimplemented `generate`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run ruff check src` and `uv run basedpyright` clean
- `cd backend && uv run pytest` green (existing suites unaffected)

#### Manual Verification:
- `cd backend && uv run python -c "from application.distill.ports import CardGeneration, NoteDocumentParser, UnitOfWork; print('ok')"`

---

## Phase 8: NoteDocumentParser — behavior

### Overview

Implement quote resolution — the rule the ADR deliberately left to this change.

### Changes Required:

#### 1. Block rendering and resolution

**File**: `backend/src/adapters/out/in_memory/distill/note_document_parser.py`

**Intent**: Decide whether a cited fragment is present in the note without rejecting an honest card over formatting alone, and without loosening into a similarity judgement that would let a paraphrase pass as grounded.

**Contract**: `resolves(content, quote)` splits the note on blank lines into blocks, and for each block and for the quote applies the same normalization: collapse every run of whitespace to a single space, strip inline emphasis markers (`*`, `_`, `` ` ``), and strip leading block markers (`#`, `>`, `-`, `+`, ordered-list prefixes). Resolution is an exact substring test of the normalized quote within a **single** normalized block; a quote spanning two blocks does not resolve. A quote that normalizes to the empty string never resolves.

#### 2. Parser contract suite

**File**: `backend/tests/unit/distill/contracts/test_note_document_parser_contract.py`

**Intent**: Pin the normalization so a later parser change cannot silently alter which historical anchors still resolve.

**Contract**: Covers verbatim resolution; resolution across differing line wrapping; resolution through `**bold**` and `` `code` `` markers; a heading's text resolving without its `#`; non-resolution of a fabricated quote; non-resolution of a cross-block quote; non-resolution of an empty and a whitespace-only quote.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/contracts/test_note_document_parser_contract.py` green
- `cd backend && uv run pytest` green

#### Manual Verification:
- `cd backend && uv run pytest tests/unit/distill/contracts/test_note_document_parser_contract.py -v` and read the case names as the statement of the matching rule

### Review r2

Artifact: `reviews/2026-09-05-r2-mutation-test-phases-2-4-8-.md`

- `R2-F1` — leading block markers must strip to empty
  Fix: assert `_normalize("# TCP Handshake") == "TCP Handshake"` (or an equivalent contract case that a heading quote resolves only when the `#` prefix is removed, not replaced)
- `R2-F2` — whitespace runs must collapse to a single space
  Fix: assert `_normalize("Connections are\nestablished") == "Connections are established"` (or a contract case that reflowed quotes still resolve after single-space collapse)

### Review r3

Artifact: `reviews/2026-09-05-r3-impl-review.md`

- `R3-F2` — `test_note_document_parser.py` duplicates the contract suite against the concrete adapter
  Fix: a deterministic in-memory adapter gets exactly one contract-parametrized suite under `contracts/`; a normalization invariant belongs there, parametrized over `_IMPLEMENTATIONS`, not in a standalone concrete-class test file
- `R3-F3` — `test_note_document_parser.py` is not named in any phase's Changes Required
  Fix: test coverage added to satisfy a Review-triage fix belongs in the plan-named contract file; do not create a new file outside any phase's Changes Required

---

## Phase 9: Deterministic CardGeneration adapter — behavior

### Overview

Implement the in-memory generator that proves the whole loop — envelope chain, grounding, discard persistence, status — before any model is wired in.

### Changes Required:

#### 1. Block-derived proposals plus one fabricated

**File**: `backend/src/adapters/out/in_memory/distill/card_generation.py`

**Intent**: Produce proposals that resolve against the note, and always one that does not, so the `Discard(ungrounded)` path is exercisable end-to-end by draining the worker rather than only in unit tests.

**Contract**: `generate(content)` splits the note on blank lines; for each block it takes the first sentence (up to the first `.`, `?`, or `!`) as `front` and the remainder as `back`, and the verbatim block text as `quote`, **skipping any block whose remainder is empty** so the adapter never emits a structurally invalid proposal. It then appends one fabricated proposal with module-constant `front` / `back` and a sentinel `quote` that no note is expected to contain. This adapter does its own paragraph split rather than reaching for `NoteDocumentParser` — it stands in for a model, and a model does not use our parser.

#### 2. Generation contract suite

**File**: `backend/tests/unit/distill/contracts/test_card_generation_contract.py`

**Intent**: Pin what any `CardGeneration` implementation owes, and pin this one's determinism.

**Contract**: Covers every proposal being non-empty on both sides; every block-derived quote resolving through `MarkdownNoteDocumentParser`; exactly one proposal whose quote does not resolve; the same content producing identical output twice; and a single-sentence-only note producing only the fabricated proposal.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/contracts/test_card_generation_contract.py` green
- `cd backend && uv run pytest` green

#### Manual Verification:
- `cd backend && uv run python -c "import asyncio;from adapters.out.in_memory.distill.card_generation import DeterministicCardGenerationAdapter as A;from domain.distill.value_objects import NoteContent;print(asyncio.run(A().generate(NoteContent(value='One. Two.\n\nThree. Four.'))))"`

---

## Phase 10: Command and handler — stubs

### Overview

Materialize the application command and the outbox handler, signatures only. This one stubs phase precedes Phases 11 and 12.

### Changes Required:

#### 1. `GenerateCardsCommand`

**File**: `backend/src/application/distill/commands/generate_cards.py`

**Intent**: Own the commit boundary for generation and hold the collaborators the domain cannot reach.

**Contract**:

```python
class GenerateCardsCommand:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        card_generation: CardGeneration,
        parser: NoteDocumentParser,
        card_factory: CardFactory,
    ) -> None: ...

    async def handle(self, note_id: NoteId) -> None: ...
```

A factory rather than a `UnitOfWork` instance, matching `SaveNoteCommand` — the command is a long-lived singleton while `OutboxWorker` dispatches concurrently.

#### 2. `FlashcardGenHandler`

**File**: `backend/src/adapters/out/worker/handlers/flashcard_gen.py`

**Intent**: Consume `note_saved` and delegate; no distill logic lives under `adapters/` beyond validation and dispatch.

**Contract**: `FlashcardGenHandler` with `envelope_type: EnvelopeType = NOTE_SAVED`, a `GenerateCardsCommand` constructor argument, and an unimplemented `async handle(envelope: OutboxEnvelope) -> None`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run ruff check src` and `uv run basedpyright` clean

#### Manual Verification:
- `cd backend && uv run python -c "from adapters.out.worker.handlers.flashcard_gen import FlashcardGenHandler; print(FlashcardGenHandler.envelope_type)"`

---

## Phase 11: GenerateCardsCommand — behavior

### Overview

Implement the orchestration the ADR assigns to the application layer, and prove every outcome including zero live cards.

### Changes Required:

#### 1. Orchestration

**File**: `backend/src/application/distill/commands/generate_cards.py`

**Intent**: Resolve what the domain cannot reach, hand each outcome to the factory, persist every minted card including discarded ones, and move the note's status exactly once.

**Contract**: `handle(note_id)` opens the unit of work, loads the note, and returns as a logged no-op when it is missing or when `distillation_status is not GENERATING` — the idempotency rule for at-least-once delivery. It calls `card_generation.generate(note.content)`; a raised exception there is logged, the note is marked failed, saved, committed, and the call returns. Otherwise, for each proposal it resolves the quote through the parser, mints through `CardFactory`, and saves the card — with a `try` around the whole per-proposal body catching `CoreException`, logging, and continuing, so a structurally invalid proposal costs only itself. After the loop the note is marked ready **regardless of how many cards are live**, saved, and the unit of work committed. No outbound envelope is enqueued.

#### 2. Command tests

**File**: `backend/tests/unit/distill/test_generate_cards_command.py`

**Intent**: Pin AC-03 through AC-06 at the layer that decides them.

**Contract**: Covers the happy path persisting live cards and reaching `ready`; a run whose every proposal is unresolved reaching `ready` with zero live cards and the discarded rows persisted (AC-04, AC-06, FR-006); a generation-port failure reaching `failed` with no cards; a redelivery against a `ready` note being a logged no-op that adds no second card set; a missing note being a logged no-op; a structurally invalid proposal being skipped while its siblings survive and the note still reaching `ready`; and the unit of work rolling back when the commit is never reached. Uses stub `CardGeneration` and `NoteDocumentParser` implementations so each outcome is forced directly.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/test_generate_cards_command.py` green
- `cd backend && uv run pytest` green

#### Manual Verification:
- `cd backend && uv run pytest tests/unit/distill/test_generate_cards_command.py -v` and confirm the zero-live-cards case is named as a success

---

## Phase 12: FlashcardGenHandler — behavior

### Overview

Implement the adapter that turns a `note_saved` envelope into a command call.

### Changes Required:

#### 1. Validate and delegate

**File**: `backend/src/adapters/out/worker/handlers/flashcard_gen.py`

**Intent**: Keep envelope shape knowledge at the adapter boundary and let a shape defect die there rather than burning `max_attempts` on something retrying cannot fix.

**Contract**: `handle` validates `envelope.payload` through `NoteSavedPayload.model_validate`, logging the exception and returning without raising on `ValidationError` — the same acked-not-retried path `SaveNoteHandler` takes. On success it calls `command.handle(NoteId(value=payload.note_id))`.

#### 2. Handler tests

**File**: `backend/tests/unit/distill/test_flashcard_gen_handler.py`

**Intent**: Pin the dispatch and the malformed-envelope path.

**Contract**: Covers a well-formed envelope reaching the command with the right `NoteId`; a malformed payload logging and returning without raising and without calling the command; and `envelope_type` being `NOTE_SAVED`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/test_flashcard_gen_handler.py` green
- `cd backend && uv run pytest` green

#### Manual Verification:
- `cd backend && uv run pytest tests/unit/distill -v`

---

## Phase 13: Composition

### Overview

Wire everything into the composition root, register the new exception codes, and put the handlers in the order the worker needs.

### Changes Required:

#### 1. Policy configuration

**File**: `backend/src/config/settings.py`

**Intent**: Let the composition root supply the policy's numbers so the domain defines the rule without reading configuration.

**Contract**: Adds `card_front_max: int = 200` and `card_back_max: int = 600`.

#### 2. Composition wiring

**File**: `backend/src/adapters/compose.py`

**Intent**: Build the card half of distill over the same outbox store capture and note-save already share.

**Contract**: Adds module-level `_distill_card_repository`, `_note_document_parser`, `_card_generation`, and `_card_factory = CardFactory(CardLengthPolicy(front_max=_settings.card_front_max, back_max=_settings.card_back_max))`. `_distill_unit_of_work()` gains the card repository. Adds `_generate_cards_command` and `_flashcard_gen_handler`, and the `OutboxWorker` handler list becomes `[_save_note_handler, _flashcard_gen_handler]` — **in that order**, so one `run_once()` drains the chain.

#### 3. Exception mapping

**File**: `backend/src/adapters/http/errors.py`

**Intent**: Satisfy the recursive exhaustiveness test, which requires an entry per `CoreException` subclass regardless of HTTP reachability.

**Contract**: Adds `empty_card_side: 422`, `card_side_too_long: 422`, `empty_anchor: 422`, `identical_card_sides: 422`, `invalid_distillation_transition: 409`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest` green, including the exhaustiveness test
- `cd backend && uv run ruff check src` and `uv run basedpyright` clean

#### Manual Verification:
- Run the backend, complete a capture session, approve the draft, then poll `/_outbox` and confirm `note_approved` and `note_saved` both reach `consumed`

---

## Phase 14: Acceptance scenarios for US-02 and US-03

### Overview

Express AC-03 through AC-06 in Gherkin against the composed in-memory system, and build the support the scenarios need. This is the first acceptance coverage the distill pillar has.

### Changes Required:

#### 1. Feature files

**File**: `backend/tests/features/distill-flow/US-02-cards-without-asking.feature`, `backend/tests/features/distill-flow/US-03-grounded-cards.feature`

**Intent**: State the slice's acceptance surface in the effort's own language.

**Contract**: US-02 carries `@distill-flow @AC-03` (cards exist for a held note with no user request, reached through capture's approve flow plus one outbox drain) and `@distill-flow @AC-04` (a held note that yields no live cards ends `ready`, differing only in card count). US-03 carries `@distill-flow @AC-05` (every live card's quote resolves within its note) and `@distill-flow @AC-06` (a proposal whose quote is absent is persisted discarded and is not among the live cards). The AC-04 scenario seeds a note into distill directly and enqueues `note_saved` rather than driving capture's HTTP, because forcing a zero-live-card outcome through a generated draft would be fragile.

#### 2. Distill composition support

**File**: `backend/tests/integration/support/in_memory_distill.py`

**Intent**: Give acceptance tests a distill half wired over capture's outbox store, so the chain under test is the real one.

**Contract**: `InMemoryDistillComposition` with a `create(outbox_store)` classmethod holding the note repository, card repository, parser, generation adapter, card factory, a `unit_of_work()` builder, and a `worker()` returning an `OutboxWorker` over `[SaveNoteHandler, FlashcardGenHandler]` with an `InMemoryOutboxClaimer` on the shared store.

#### 3. Step definitions and registration

**File**: `backend/tests/bdd/steps/distill.py`, `backend/tests/bdd/conftest.py`, `backend/tests/bdd/test_features.py`, `backend/pyproject.toml`

**Intent**: Wire the scenarios into the existing loader and register the marker the filter needs.

**Contract**: `conftest.py` gains a `distill_composition` fixture depending on `capture_composition` so both halves share one `outbox_store`. `steps/distill.py` adds the drain step (`asyncio.run(worker.run_once())`), the seed-a-held-note step, and the assertion steps for held status, live-card count, quote resolution, and discarded rows. `test_features.py` gains `"bdd.steps.distill"` in `pytest_plugins`. `pyproject.toml` gains `"distill-flow: distill-flow effort acceptance scenarios"` to `markers`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/bdd -m "distill-flow" -v` green with four scenarios
- `cd backend && uv run pytest` green
- `cd backend && uv run pytest tests/bdd --collect-only` reports no undefined steps

#### Manual Verification:
- `cd backend && uv run pytest tests/bdd -m "distill-flow and AC-04" -v` and confirm the zero-card scenario passes as a completed distillation

---

## Testing Strategy

### Unit Tests:

Card value objects and the length policy (Phase 2); the differing-sides invariant and the factory's fixed ordering (Phase 4); note transitions and their guard (Phase 6); the command's six outcomes including zero live cards, generation failure, redelivery no-op, and per-proposal skip (Phase 11); the handler's dispatch and malformed-envelope path (Phase 12).

### Integration Tests:

Port contract suites, one per port, parametrized over implementations: `CardRepository` and the renamed `NoteRepository` (Phase 6), `NoteDocumentParser` (Phase 8), `CardGeneration` (Phase 9). Per the contract-testing rule the in-memory implementation runs on every CI invocation; a later model-backed `CardGeneration` runs the same suite on a non-blocking cadence.

### Manual Testing Steps:

Run the backend, complete a capture session, approve the draft, and poll `/_outbox` to confirm both envelopes reach `consumed` (Phase 13). There is no read surface for notes or cards until S-03/S-04, so the outbox endpoint is the only human-visible evidence the chain ran.

## Performance Considerations

Generation is a per-envelope batch over a single note's blocks, bounded by `NOTE_CONTENT_MAX_LENGTH` (20 000 chars), so proposal counts stay small and the parser's per-proposal normalization is linear in note length. `list_by_note` is a full scan of the in-memory card dict; when a SQL adapter lands, `discard IS NULL` must be indexed so "not discarded" stays a cheap predicate — the ADR records this as the cost of a nullable value object over a status column.

## Migration Notes

`NoteRepository.add` is renamed to `save` — a shipped, tested S-01 symbol. Blast radius is four files: the port, the in-memory adapter, one call site in `SaveNoteCommand`, and three cases in the note contract suite. No capture code touches distill's port, and no persisted data exists to migrate under InMemoryFirst.

## References

- `context/adrs/distill-domain-shape/decision.md:27-116` — authoritative domain shape, factory and policy rules, boundary rules, outbox chain
- `context/efforts/distill-flow/roadmap.md:38-44` — S-02 slice and AC-03–AC-06
- `context/efforts/distill-flow/stories.md:21-37` — US-02, US-03
- `context/efforts/distill-flow/prd.md:44-48` — FR-002–FR-006
- `context/changes/distill-flow-grounded-generation/research.md` — S-01 baseline and the S-02 gap analysis
- `context/foundation/rules/layering.md`, `cqrs-lite.md`, `exceptions.md`, `contract-testing.md`, `code-ordering.md`
- `context/foundation/test-stack.md` — pytest, pytest-bdd, marker filters
- `context/archive/changes/2026-09-03-distill-flow-note-lands/plan.md` — S-01, the phase shape this plan follows

Execution state for this plan lives in `todos.md`, sibling of this file.
