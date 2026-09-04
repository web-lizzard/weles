# Note Lands in Distill — Implementation Plan

## Overview

Slice S-01 of the `distill-flow` effort (AC-01, AC-02). The first of distill's two outbox consumers: a `note_approved` envelope, already produced by capture on approval, gets a real handler that persists distill's own `Note` aggregate in `generating` status and enqueues `note_saved` for S-02's flashcard-gen to pick up later. This replaces the placeholder `LoggingNoteSaveHandler`, which today only logs the payload and persists nothing.

Execution state for this plan lives in `todos.md`, sibling of this file.

## Current State Analysis

`domain/distill/` and `application/distill/` do not exist yet. What exists and this slice builds on:

- `NoteApprovedPayload` (`domain/capture/outbox.py:19-43`) — the denormalized snapshot capture already enqueues atomically with approval, carrying `note_id`, `session_id`, `topic{id,label}`, `content`, `tags[{id,label}]`, `approved_at`.
- `OutboxHandler` protocol (`application/shared/outbox/ports.py:6-9`) — `envelope_type` + `async handle(envelope)`, dispatched by `OutboxWorker`.
- `LoggingNoteSaveHandler` (`adapters/out/worker/handlers/note_save.py:9-18`) — validates the payload and logs; this slice's `SaveNoteHandler` replaces it.
- `InMemoryOutboxStore`/`InMemoryOutboxAppender` (`adapters/out/in_memory/shared/outbox/`) — the shared queue capture's `ApproveNoteCommand` already writes into; distill's `UnitOfWork` must be built over the **same store instance**, or the worker never sees what capture enqueues.
- Capture's own `NoteRepository`/`UnitOfWork`/`InMemoryUnitOfWork` (`domain/capture/ports.py:22-26`, `application/capture/ports.py:39-52`, `adapters/out/in_memory/capture/unit_of_work.py`) — the shape this slice's distill-owned equivalents mirror, at a smaller port surface.
- `compose.py:63-70` — registers `_note_save_handler` in the `OutboxWorker`'s handler list; this slice's Phase 9 rewires that registration.

Key constraint discovered: `OutboxWorker.run_once()` (`adapters/out/worker/outbox_worker.py:40-43`) processes every envelope a handler claims **concurrently** via `asyncio.gather`, calling the same handler instance's `handle()` once per envelope in parallel. A handler that holds one long-lived `UnitOfWork` instance would race two concurrent snapshot/restore cycles against each other — see `## Critical Implementation Details`.

## Desired End State

An approved note reaches distill with no user action: `POST /capture-sessions/{id}/approval` enqueues `note_approved` as it already does today; within one worker poll, `SaveNoteHandler` persists a distill `Note` (`distillation_status=generating`) and enqueues exactly one `note_saved` envelope. Redelivering the same `note_approved` envelope is a no-op — the note is not written twice and no second `note_saved` is enqueued. A malformed envelope is logged and acknowledged rather than retried.

Verify via the unit and contract test suites below, plus a manual pass through the existing `/_outbox` debug endpoint (non-prod) confirming the envelope chain: `note_approved` → `consumed`, and a new `note_saved` envelope appears `pending` then `consumed` after the next `run_once()`.

### Key Discoveries:

- `Note.draft_note`/`Topic.mint`/`Tag.mint` in capture put minting logic as classmethods directly on the aggregate (`domain/capture/note.py:32-49`) because those calls take only pure domain arguments. Mapping a wire payload onto an aggregate is a different kind of construction — **decided in this plan**: distill's `Note` carries no such classmethod; a standalone module-level factory function (`mint_note`) takes only distill's own value objects, never a payload type, so neither the aggregate nor the factory needs to know an outbox envelope exists.
- The boundary rule (`context/adrs/distill-domain-shape/decision.md:107`) — `domain/distill/` and `application/distill/` import nothing from `domain/capture/` or `application/capture/` — is stricter than where the existing stub sits: `LoggingNoteSaveHandler` imports capture's `NoteApprovedPayload` at the **adapter** layer, which the ADR's own research explicitly allows. It does not allow that import to reach `application/distill/commands/save_note.py`. The adapter is therefore the only place capture's payload type is named; it unpacks the payload into distill's own value objects before calling into the application command.
- `InMemoryUnitOfWork` (capture's, `adapters/out/in_memory/capture/unit_of_work.py:64-84`) resets its snapshot state fresh on every `__aenter__`, so nothing prevents *sequential* reuse of one instance — only *concurrent* reuse is unsafe. `OutboxWorker.run_once()` gathers concurrently (`outbox_worker.py:40-43`), so distill's `SaveNoteCommand` must build a fresh `UnitOfWork` per `handle()` call rather than close over one built at composition time.

## What We're NOT Doing

- **Card generation, `CardRepository`, `CardFactory`, `flashcard-gen`.** All of S-02.
- **`distillation_status` transitions to `ready`/`failed`.** S-01 only ever writes `generating`.
- **Any read/query surface for distill notes.** No `GET`, no DTO. S-03 onward.
- **The full `UnitOfWork` member set from the ADR.** `application/distill/ports.py`'s `UnitOfWork` in this plan declares only `notes` and `outbox` — the two ports this slice's code calls. `cards: CardRepository` is added when S-02 plans it.
- **A distill-owned mirror of `NoteApprovedPayload`.** The adapter reuses capture's existing type for validation, exactly as the current stub does; the ADR's own boundary rule targets domain/application imports, not a shared DTO shape at the adapter layer.
- **Poison-message surfacing beyond a log line.** A malformed envelope is logged and acked; no dead-letter table, no alerting.

## Implementation Approach

Two seams carry this slice, mirroring the two-handler chain the ADR already settled:

**The adapter is the only capture import.** `SaveNoteHandler` validates `envelope.payload` through capture's `NoteApprovedPayload` — the one place this plan reuses a capture type — then unpacks its fields into distill's own value objects (`NoteId`, `SessionId`, `TopicSnapshot`, `TagSnapshot`, `NoteContent`) before calling `SaveNoteCommand.handle(...)`. Everything downstream of the adapter, including the command's own signature, never names a capture type.

**Idempotency falls out of shared identity, not a lookup table.** `SaveNoteCommand.handle()` checks `uow.notes.get(note_id)` first; a hit means this `note_id` was already saved (whatever attempt number this delivery is), so it logs a distinct no-op line and returns without a second `mint_note`/`add`/`append`. A miss mints, persists, enqueues `note_saved`, and commits — all inside one `UnitOfWork`.

## Critical Implementation Details

`SaveNoteHandler` and `SaveNoteCommand` are constructed once in `compose.py` and registered as a single long-lived entry in `OutboxWorker`'s handler list, which `run_once()` calls concurrently across every envelope it claims in one batch (`outbox_worker.py:27-44`, `asyncio.gather`). A command holding one pre-built `UnitOfWork` instance would race two concurrent `async with` blocks over the same snapshot dict. `SaveNoteCommand` is therefore constructed with a **`UnitOfWork` factory** (`Callable[[], UnitOfWork]`), not a `UnitOfWork` instance, and calls it fresh inside every `handle()` — the same one-instance-per-transaction discipline `compose.py`'s own `_unit_of_work()` gives capture's per-request commands, adapted for a singleton consumer that serves many concurrent transactions instead of one per HTTP request.

---

## Phase 1: Note domain model — stubs

### Overview

Materializes distill's value objects, exceptions and the `Note` aggregate as importable symbols with no behavior. `mint_note` is named here as a signature only — a standalone module-level function, not a method on `Note`.

### Changes Required:

#### 1. Distill domain package

**File**: `backend/src/domain/distill/__init__.py`

**Intent**: Open the `domain/distill/` bucket the ADR assigns this module.

**Contract**: Empty package marker.

#### 2. Value objects

**File**: `backend/src/domain/distill/value_objects.py`

**Intent**: Distill's own identity and snapshot types — never capture's — per the boundary rule. `TopicSnapshot`/`TagSnapshot` mirror capture's `VocabularySnapshot` exactly (no validation of their own; the label was already validated when capture resolved it). `NoteId`/`SessionId` carry no `.new()` — both are always sourced from an existing `note_approved` payload, never minted fresh in distill.

**Contract**:

```python
NOTE_CONTENT_MAX_LENGTH = 20000

class NoteId(BaseModel, frozen=True):
    value: UUID

class SessionId(BaseModel, frozen=True):
    value: UUID

class TopicSnapshot(BaseModel, frozen=True):
    id: UUID
    label: str

class TagSnapshot(BaseModel, frozen=True):
    id: UUID
    label: str

class NoteContent(BaseModel, frozen=True):
    value: str
    # field_validator(mode="before"): strip — implemented in Phase 2
    # model_validator(mode="after"): non-empty, len <= NOTE_CONTENT_MAX_LENGTH — implemented in Phase 2

class DistillationStatus(StrEnum):
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
```

#### 3. Value object exceptions

**File**: `backend/src/domain/distill/exceptions.py`

**Intent**: `NoteContent`'s guards raise rather than silently accept.

**Contract**: `EmptyNoteContentError`, `NoteContentTooLongError`, both `CoreException` subclasses.

#### 4. Note aggregate and factory signature

**File**: `backend/src/domain/distill/note.py`

**Intent**: The living knowledge artifact per the ADR — no immutability guard, `distillation_status` starts at `generating`. `mint_note` is a free function, not a classmethod, so `Note` never imports or references anything payload-shaped.

**Contract**:

```python
class Note(BaseModel):
    id: NoteId
    session_id: SessionId
    topic: TopicSnapshot
    content: NoteContent
    tags: list[TagSnapshot]
    distillation_status: DistillationStatus
    approved_at: datetime
    created_at: datetime


def mint_note(
    note_id: NoteId,
    session_id: SessionId,
    topic: TopicSnapshot,
    content: NoteContent,
    tags: list[TagSnapshot],
    approved_at: datetime,
) -> Note: ...
```

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run ruff check src` passes
- `cd backend && uv run basedpyright` reports no new errors
- `cd backend && uv run python -c "from domain.distill.note import Note, mint_note; from domain.distill.value_objects import NoteId, SessionId, TopicSnapshot, TagSnapshot, NoteContent, DistillationStatus"` exits 0

---

## Phase 2: Note domain model — behavior

### Overview

`NoteContent`'s validation and `mint_note`'s mapping become real, proven against pure objects.

### Changes Required:

#### 1. NoteContent validation

**File**: `backend/src/domain/distill/value_objects.py`

**Intent**: Same convention as every meaningful string in `domain/capture/value_objects.py`.

**Contract**: `value` is stripped on the way in; raises `EmptyNoteContentError` when empty after stripping, `NoteContentTooLongError` when longer than `NOTE_CONTENT_MAX_LENGTH`.

#### 2. mint_note mapping

**File**: `backend/src/domain/distill/note.py`

**Intent**: The only place a `Note` comes into being in distill.

**Contract**: Builds a `Note` with the given `id`, `session_id`, `topic`, `content`, `tags`, `approved_at`, `distillation_status=DistillationStatus.GENERATING`, and `created_at=datetime.now(UTC)`.

#### 3. Domain tests

**File**: `backend/tests/unit/distill/__init__.py`, `backend/tests/unit/distill/test_value_objects.py`, `backend/tests/unit/distill/test_note.py`

**Intent**: Prove the validation guards and the mapping without any repository or outbox involved.

**Contract**: `NoteContent` — empty raises, over-length raises, leading/trailing whitespace stripped. `mint_note` — returns a `Note` with `distillation_status == GENERATING`, `created_at` a UTC-aware timestamp near now, and every field mapped from its matching argument.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/test_value_objects.py tests/unit/distill/test_note.py -v` passes
- `cd backend && uv run pytest` passes

---

## Phase 3: NoteRepository — stubs

### Overview

Materializes the repository port and its in-memory adapter as importable symbols with no behavior.

### Changes Required:

#### 1. Repository port

**File**: `backend/src/domain/distill/ports.py`

**Intent**: Distill's own repository-style port, in its own vocabulary, per `hexagonal-arch-shape`'s domain-layer rule.

**Contract**:

```python
class NoteRepository(Protocol):
    async def add(self, note: Note) -> None: ...
    async def get(self, note_id: NoteId) -> Note | None: ...
```

#### 2. In-memory adapter package

**File**: `backend/src/adapters/out/in_memory/distill/__init__.py`

**Intent**: Mirror the existing `adapters/out/in_memory/capture/` layout.

**Contract**: Empty package marker.

#### 3. In-memory adapter skeleton

**File**: `backend/src/adapters/out/in_memory/distill/note_repository.py`

**Intent**: `InMemoryFirst` — the first, and for this slice only, adapter behind `NoteRepository`.

**Contract**:

```python
class InMemoryNoteRepository:
    def __init__(self) -> None: ...
    async def add(self, note: Note) -> None: ...
    async def get(self, note_id: NoteId) -> Note | None: ...
    def snapshot(self) -> dict[UUID, Note]: ...
    def restore(self, snapshot: dict[UUID, Note]) -> None: ...
```

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run ruff check src` passes
- `cd backend && uv run basedpyright` reports no new errors

---

## Phase 4: NoteRepository — behavior

### Overview

The contract this port must satisfy, mirroring capture's `NoteRepository` contract suite exactly.

### Changes Required:

#### 1. Repository implementation

**File**: `backend/src/adapters/out/in_memory/distill/note_repository.py`

**Intent**: Dict-backed, keyed by the note id's `UUID` value; a second `add` with the same id overwrites.

**Contract**: `add`/`get` operate over an internal `dict[UUID, Note]` keyed by `note_id.value`. `snapshot`/`restore` deep-copy, for the `UnitOfWork`'s rollback (Phase 5).

#### 2. Contract test suite

**File**: `backend/tests/unit/distill/contracts/__init__.py`, `backend/tests/unit/distill/contracts/test_note_repository_contract.py`

**Intent**: One behavioral contract per port, parametrized over implementations, per the contract-testing rule — same shape as `tests/unit/capture/contracts/test_note_repository_contract.py`.

**Contract**: Add-then-get returns the saved note; get on an unknown id returns `None`; a second add with the same id overwrites.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/contracts/test_note_repository_contract.py -v` passes
- `cd backend && uv run pytest` passes

---

## Phase 5: Application layer and outbound envelope — stubs

### Overview

Materializes the `UnitOfWork` port, its in-memory adapter, the `note_saved` envelope type, and `SaveNoteCommand`'s signature. Everything except `SaveNoteCommand.handle()`'s body is fully implemented here: the `UnitOfWork` adapter and the envelope type are pure wiring/data with no independent test, verified indirectly through Phase 6's command behavior.

### Changes Required:

#### 1. UnitOfWork port

**File**: `backend/src/application/distill/ports.py`, `backend/src/application/distill/__init__.py`

**Intent**: Distill's own `UnitOfWork`, scoped to what this slice calls — `cards` joins when S-02 plans it. A handler never holds two modules' units of work.

**Contract**:

```python
class UnitOfWork(Protocol):
    notes: NoteRepository
    outbox: OutboxAppender

    async def __aenter__(self) -> "UnitOfWork": ...
    async def __aexit__(self, *exc: object) -> None: ...
    async def commit(self) -> None: ...
```

#### 2. In-memory UnitOfWork

**File**: `backend/src/adapters/out/in_memory/distill/unit_of_work.py`

**Intent**: Mirrors capture's `InMemoryUnitOfWork` shape at the smaller member set: snapshot on enter, restore on exit unless committed.

**Contract**: `InMemoryUnitOfWork.__init__(self, notes: InMemoryNoteRepository, outbox_store: InMemoryOutboxStore, outbox: InMemoryOutboxAppender) -> None`. `__aenter__` snapshots `notes` and the outbox store; `__aexit__` restores both when `commit()` was never called; `commit()` sets the committed flag. Fully implemented now — no independent test; exercised through Phase 6's `SaveNoteCommand` tests, matching capture's own `InMemoryUnitOfWork` (which has no standalone test either).

#### 3. Outbound envelope type

**File**: `backend/src/domain/distill/outbox.py`

**Intent**: The `note_saved` envelope note-save enqueues once per note, in the same transaction as the save. Minimum payload per the plan's Key Decisions — S-02 reads the note back through `NoteRepository.get`.

**Contract**:

```python
NOTE_SAVED = EnvelopeType(name="note_saved")

class NoteSavedPayload(BaseModel, frozen=True):
    note_id: UUID

    def to_envelope(self) -> OutboxEnvelope:
        return OutboxEnvelope.pending(NOTE_SAVED, self.model_dump(mode="json"))
```

Fully implemented now — the mapping is a one-field wrap with nothing to assert beyond what Phase 6's command test already covers when it inspects the enqueued envelope.

#### 4. SaveNoteCommand skeleton

**File**: `backend/src/application/distill/commands/save_note.py`, `backend/src/application/distill/commands/__init__.py`

**Intent**: The application command note-save's handler adapter delegates to. Takes a `UnitOfWork` **factory**, not an instance — see `## Critical Implementation Details`. Its signature names only distill's own value objects, never a capture type.

**Contract**:

```python
class SaveNoteCommand:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None: ...

    async def handle(
        self,
        note_id: NoteId,
        session_id: SessionId,
        topic: TopicSnapshot,
        content: NoteContent,
        tags: list[TagSnapshot],
        approved_at: datetime,
    ) -> None: ...
```

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run ruff check src` passes
- `cd backend && uv run basedpyright` reports no new errors

---

## Phase 6: SaveNoteCommand — behavior

### Overview

The idempotent save: mint, persist, enqueue `note_saved`, commit — or no-op on redelivery.

### Changes Required:

#### 1. Idempotent handle()

**File**: `backend/src/application/distill/commands/save_note.py`

**Intent**: Redelivery of the same `note_id` must not persist twice or enqueue a second `note_saved`.

**Contract**: Builds a fresh `UnitOfWork` from `self._uow_factory()`. Inside `async with uow`: `existing = await uow.notes.get(note_id)`; if not `None`, log one line identifying the no-op redelivery (distinct from a first save) and return without committing. Otherwise `mint_note(...)`, `await uow.notes.add(note)`, `await uow.outbox.append(NoteSavedPayload(note_id=note_id.value).to_envelope())`, `await uow.commit()`.

#### 2. Command tests

**File**: `backend/tests/unit/distill/test_save_note_command.py`

**Intent**: Same `_Stack`-fixture style as `tests/unit/capture/test_approve_note_command.py`.

**Contract**: First call persists the note in `generating` and enqueues exactly one `note_saved` envelope carrying the note's id. A second call with the same `note_id` (simulating redelivery) leaves the store at one note and the outbox at one `note_saved` envelope, and asserts the distinct no-op log line via `caplog`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/test_save_note_command.py -v` passes
- `cd backend && uv run pytest` passes

---

## Phase 7: Handler adapter — stubs

### Overview

Adds `SaveNoteHandler` alongside the existing `LoggingNoteSaveHandler` — the stub is not removed yet; Phase 9 rewires `compose.py` to the new handler and deletes the stub in the same change, so the tree stays buildable at every phase.

### Changes Required:

#### 1. Handler skeleton

**File**: `backend/src/adapters/out/worker/handlers/note_save.py`

**Intent**: The adapter that owns the one capture import this plan makes (`NoteApprovedPayload`, for validation only), and the one place that decides malformed vs. valid.

**Contract**:

```python
class SaveNoteHandler:
    envelope_type: EnvelopeType = NOTE_APPROVED

    def __init__(self, command: SaveNoteCommand) -> None: ...

    async def handle(self, envelope: OutboxEnvelope) -> None: ...
```

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run ruff check src` passes
- `cd backend && uv run basedpyright` reports no new errors

---

## Phase 8: Handler adapter — behavior

### Overview

Validates the envelope, dispatches to `SaveNoteCommand` on success, logs and acks on a malformed payload.

### Changes Required:

#### 1. handle() implementation

**File**: `backend/src/adapters/out/worker/handlers/note_save.py`

**Intent**: A malformed envelope is not retryable — the shape is wrong, not the timing — so the worker acks it rather than burning `max_attempts` retries on something a retry can never fix.

**Contract**: `NoteApprovedPayload.model_validate(envelope.payload)` inside a `try`; on `pydantic.ValidationError`, log an error identifying the envelope and return (no exception propagates, so `OutboxWorker` acks it as consumed). On success, unpack the payload into distill's own value objects — `NoteId(value=payload.note_id)`, `SessionId(value=payload.session_id)`, `TopicSnapshot(id=payload.topic.id, label=payload.topic.label)`, `NoteContent(value=payload.content)`, `[TagSnapshot(id=tag.id, label=tag.label) for tag in payload.tags]`, `payload.approved_at` — and call `self._command.handle(...)` with them.

#### 2. Handler tests

**File**: `backend/tests/unit/distill/test_save_note_handler.py`

**Intent**: Prove both branches without a real `OutboxWorker`.

**Contract**: A well-formed envelope calls `SaveNoteCommand.handle()` with the correctly unpacked value objects (assert via a fake/spy command). A malformed envelope (e.g. missing `note_id`) does not call the command, raises nothing, and logs — assert via `caplog`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/test_save_note_handler.py -v` passes
- `cd backend && uv run pytest` passes

---

## Phase 9: Composition

### Overview

Wiring: distill's repository, `UnitOfWork` factory, command and handler, sharing capture's outbox store; the stub handler is deleted here, in the same change that stops registering it. Not TDD'able — composition-root configuration whose behavior is already covered by the phases above.

### Changes Required:

#### 1. Composition root

**File**: `backend/src/adapters/compose.py`

**Intent**: One outbox store instance behind both modules' appenders, or the worker never sees what capture enqueues. `SaveNoteCommand` is built with a factory function, not a shared `UnitOfWork` instance, per `## Critical Implementation Details`.

**Contract**: Module-level `_distill_note_repository = InMemoryNoteRepository()` (distill's). A `_distill_unit_of_work() -> UnitOfWork` factory function builds a fresh `InMemoryUnitOfWork(_distill_note_repository, _outbox_store, _outbox_appender)` per call, reusing the same `_outbox_store`/`_outbox_appender` module-level instances capture's `_unit_of_work()` already shares. `_save_note_command = SaveNoteCommand(uow_factory=_distill_unit_of_work)`; `_save_note_handler = SaveNoteHandler(_save_note_command)`, replacing `_note_save_handler` in `_outbox_worker`'s handler list.

#### 2. Remove the stub

**File**: `backend/src/adapters/out/worker/handlers/note_save.py`

**Intent**: `LoggingNoteSaveHandler` has no remaining reference once `compose.py` registers `SaveNoteHandler` instead.

**Contract**: Delete the `LoggingNoteSaveHandler` class and its now-unused imports (`domain.capture.outbox.NoteApprovedPayload` import moves to wherever `SaveNoteHandler.handle()` already uses it — no duplicate import remains).

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest` passes
- `cd backend && uv run ruff check src` passes
- `cd backend && uv run basedpyright` reports no new errors

#### Manual Verification:
- `cd backend && uv run fastapi dev src/main.py`, then approve a note through the existing `POST /capture-sessions/{id}/approval` flow
- `curl http://localhost:8000/_outbox` (non-prod) shows the `note_approved` envelope as `consumed` and a `note_saved` envelope appearing `pending`, then `consumed` after the next worker poll

---

## Testing Strategy

### Unit Tests:

`NoteContent`'s validation guards; `mint_note`'s field mapping and `generating` status; `NoteRepository`'s add/get/overwrite contract; `SaveNoteCommand`'s first-save vs. idempotent-redelivery paths, including the enqueued `note_saved` envelope and the distinct no-op log line; `SaveNoteHandler`'s valid-payload dispatch and malformed-payload log-and-ack.

### Integration Tests:

None added by this plan — no HTTP surface changes. The existing `/_outbox` endpoint (`tests/integration/test_outbox_http.py`) already exercises the shared store this slice's worker also reads from.

### Manual Testing Steps:

1. `cd backend && uv run fastapi dev src/main.py`
2. Start a capture session, draft a note, approve it (existing flow).
3. `curl http://localhost:8000/_outbox` — the `note_approved` envelope moves to `consumed` within one poll interval, and a `note_saved` envelope appears.

## Performance Considerations

None beyond what the existing `OutboxWorker` already bounds (poll interval, batch size, max attempts) — this slice adds one more handler to an existing loop, not a new execution path.

## Migration Notes

None — greenfield module, no existing distill data.

## References

- `context/adrs/distill-domain-shape/decision.md:27-33` — Note aggregate fields and `distillation_status` rules
- `context/adrs/distill-domain-shape/decision.md:84-92` — two-handler outbox chain and idempotency
- `context/adrs/distill-domain-shape/decision.md:94-101` — ports and handler-as-adapter pattern
- `context/adrs/distill-domain-shape/decision.md:107` — boundary rule (no capture imports from domain/application)
- `context/efforts/distill-flow/roadmap.md:31-36` — S-01 scope and acceptance criteria
- `context/efforts/distill-flow/stories.md:12-19` — US-01, AC-01, AC-02
- `context/changes/distill-flow-note-lands/research.md` — domain model research this plan resolves the two open questions from
- `backend/src/domain/capture/outbox.py:11-43` — `NoteApprovedPayload`/`VocabularySnapshot` shape this plan reuses at the adapter layer
- `backend/src/adapters/out/worker/outbox_worker.py:27-44` — concurrent `asyncio.gather` dispatch driving the `UnitOfWork`-factory decision
- `backend/src/adapters/out/in_memory/capture/unit_of_work.py:26-85` — snapshot/restore `UnitOfWork` pattern this plan mirrors
- `backend/tests/unit/capture/contracts/test_note_repository_contract.py` — contract test shape this plan mirrors
- `backend/tests/unit/capture/test_approve_note_command.py` — command test `_Stack` fixture style this plan mirrors
