# Reshape and Approve the Draft into the Outbox — Implementation Plan

## Overview

Slice S-06 of the `capture-flow` effort. The draft note that S-04 produces becomes something the user can push back on and then deliberately hand over: a conversational redraft loop mutates the single draft in place, an explicit `/approve` closes the session and drops a `note_approved` envelope into a shared outbox, and a background worker running in the same event loop claims that envelope and processes it. This realizes AC-12 (the draft is shown before anything is saved), AC-13 (conversational redraft, no direct text editing), AC-14 (nothing reaches the outbox without explicit approval) and AC-15 (approval sends the note and ends the session).

The slice is vertical and introduces the first tenant of a new shared layer: `domain/shared/outbox/`. It also introduces the first background execution in this codebase — an `asyncio.Task` living beside the API in one process, which the cheap-VPS constraint from `overview-thougts` requires.

Execution state for this plan lives in `todos.md`, sibling of this file.

## Current State Analysis

Capture runs end to end up to a persisted draft. `POST /capture-sessions` opens a session; `POST /capture-sessions/{id}/messages` streams a turn over SSE; when the model recognizes a confirmation phrase it emits draft chunks, `VocabularyResolver` reconciles topic and tag labels against existing rows, and `CaptureSession.draft_note()` produces a `Note` in status `draft`.

What exists:

- `CaptureSession` (`backend/src/domain/capture/capture_session.py:22`) — `id`, `topic: SessionTopic | None`, `note_id: NoteId | None`, `status`, `created_at`, with `start()`, `assign_topic()` and `draft_note()`. There is no `approve()` and no `close()`.
- `Note` (`backend/src/domain/capture/note.py:17`) — carries `status: NoteStatus` and `approved_at: datetime | None`, both of which nothing ever moves off their initial values. `draft()` is the only operation; there are no mutators and no `approve()`.
- `NoteStatus` (`backend/src/domain/capture/value_objects.py:40`) already has `APPROVED`; nothing sets it.
- Domain ports (`backend/src/domain/capture/ports.py`) — five repositories, all capture-scoped. There is no `domain/shared/` package at all.
- `UnitOfWork` (`backend/src/application/capture/ports.py:37`) — five repository members, `__aenter__`/`__aexit__`/`commit()`. `InMemoryUnitOfWork` (`backend/src/adapters/out/in_memory/capture/unit_of_work.py:20`) implements rollback by snapshotting each store on enter and restoring on exit unless `commit()` ran.
- `GenerateReplyCommand.handle()` (`backend/src/application/capture/commands/send_message.py:70`) — one `UnitOfWork` per turn, routes `ReplyChunk`s, calls `session.draft_note(...)` at end of stream, commits, then yields `draft_done` followed by `done`.
- `ReplyChunk` union (`backend/src/application/capture/value_objects.py:92`) — `reply` / `topic` / `tag` / `note`, discriminated on `kind`.
- SSE event union (`backend/src/application/capture/dto.py:62`) — discriminated on `type`, mirrored by hand in `tui/src/api/stream.ts`.
- TUI (`tui/src/screens/CaptureScreen.tsx`) — renders `DraftNotePanel` from store state; `TextInput` already loses focus while streaming (`CaptureScreen.tsx:83`), so modal input handling is an established pattern here.
- `Settings` (`backend/src/config/settings.py:6`) — `database_url`, `notion_api_token`, `vocabulary_match_threshold`. No environment discriminator.
- `main.py` (`backend/src/main.py`) — bare `FastAPI()` with two routers and one exception handler. **No lifespan handler exists yet.**

What is missing: everything outbox-shaped (`domain/shared/` does not exist), `Note` mutators and `approve()`, `CaptureSession.approve()`/`close()`, any second entry point besides the message stream, any background execution, and any TUI affordance for approving.

Key constraints discovered:

- `EXCEPTION_STATUS_MAP` (`backend/src/adapters/http/errors.py:6`) is guarded by an exhaustiveness test walking `CoreException.__subclasses__()`. Every exception this slice adds — including ones under `domain/shared/` — needs an entry, or the test fails.
- `tests/bdd/test_features.py:7` registers step modules explicitly in `pytest_plugins`; a new step module that is not listed there never loads.
- `backend/pyproject.toml` declares pytest markers only up to `AC-11`. `AC-12`–`AC-15` must be added or `-m "AC-14"` matches nothing and pytest warns on unknown markers.
- `InMemoryUnitOfWork` snapshots each store explicitly; a repository that does not join the snapshot set silently loses the rollback guarantee.
- `tui/src/api/stream.ts` is a hand-declared mirror of the SSE payloads because `openapi-typescript` cannot express FastAPI's SSE union; the plain JSON approval endpoint has no such problem and goes through the generated client.

## Desired End State

The user talks through a topic, confirms they are done, and the draft panel fills in. They type a plain-language change ("make it shorter, and drop the second tag"); the agent redrafts, and the same `Note` row — same `note_id` — comes back mutated. They repeat that as often as they like. When satisfied they type `/approve`. The TUI does not send that as a conversational turn; it calls the approval endpoint. The note flips to `approved`, the session flips to `closed`, a `note_approved` envelope lands in the outbox in the same transaction, and the draft panel is replaced by `✓ Approved — queued for saving` with the input permanently unfocused. Within a poll interval the worker task claims the envelope, the stub handler logs the payload, and the envelope reaches `consumed` — visible at `GET /_outbox` outside production.

Verify by running the backend and the TUI and walking that path, watching the worker log line appear in the backend console. Automated verification is the AC-12–AC-15 acceptance scenarios plus the unit and integration suites.

### Key Discoveries:

- `status: closed` on `CaptureSession` means specifically "approved, note sent" (`context/adrs/capture-flow-domain-shape/decision.md:44`), not a generic terminal state. This slice is what finally makes the `status == open` guard on `draft_note()` reachable through HTTP.
- The redraft loop "mutates the single draft in place" (`decision.md:37`) and **does not re-enter `draft_note()`** — which is why `SessionNoteAlreadyDraftedError` can stay exactly as it is. Drafting and reshaping are two different operations on two different objects.
- The ADR leaves lazy reconstruction of `Topic`/`Tag` from stored ids "named but not designed" and hands it to `/plan`. **Decided here:** `ApproveNoteCommand` loads them from `uow.topics`/`uow.tags` at approve time, inside the transaction it already holds. Approval is the only place in this slice that needs the full objects, and it needs them once, so no loader, proxy, or eager-hydration mechanism is introduced.
- The duck session `outbox-shared` settles the envelope's field set, the denormalized `note_approved` payload, and enqueue-as-a-`UnitOfWork`-member. It explicitly parks the claim algorithm; this slice unparks the minimal half of it (atomic claim) and leaves lease/reclaim parked — see `## Migration Notes`.
- `GenerateReplyCommand.handle()` already models the failure semantics this slice needs: stream inside the `UnitOfWork`, build the terminal event inside, yield it after `commit()` (`send_message.py:153-163`). Nothing tells the client "saved" before the save happened, and the redraft branch inherits that for free.
- `DeterministicReplyGenerationAdapter` (`backend/src/adapters/out/in_memory/capture/reply_generation.py:41`) decides to draft when the last user message matches a closed phrase list. The redraft branch needs no new signal from the port: a turn taken while `session.note_id` is set is by definition a redraft turn.

## What We're NOT Doing

- **A SQL/Postgres outbox table.** In-memory adapters only, per the `InMemoryFirst` rule and the duck session's explicit S-06 scoping.
- **Lease / reclaim of abandoned `processing` envelopes.** A worker that crashes mid-handle strands its envelope. Deliberate — see `## Migration Notes`.
- **A real `distill` consumer.** The registered handler logs the payload and returns; it exists to prove the claim → handle → ack chain and is expected to be replaced wholesale.
- **A second producer.** Whether note-save enqueues a follow-up envelope for flashcard-gen stays parked, exactly as the duck session left it.
- **Reading notes back.** No `GET /notes/{id}`, no note DTO. The approved note reaches the client through the approval response and nowhere else.
- **An ADR amendment for the `domain/shared/` bucket.** The duck session recorded this debt against `hexagonal-arch-shape`, whose directory convention still shows no shared bucket. It was deliberately left out of this slice's scope — see `## Open Risks` in `plan-brief.md`.
- **A `discarded` transition.** `NoteStatus.DISCARDED` remains the ADR's unreachable extension point.
- **Starting a new session from the TUI after approval.** The screen ends on a confirmation; a new topic means restarting the TUI.

## Implementation Approach

Three seams carry this slice.

**The shared outbox.** `domain/shared/outbox/` holds a generic `OutboxEnvelope` whose status transitions are domain methods, plus two narrow ports split by role: `OutboxAppender.append(...)` for the producer and `OutboxClaimer.claim/ack/fail` for the consumer. The split matters because the two sides have incompatible transaction stories — the producer's write is a member of capture's `UnitOfWork` and commits with the note, while the consumer's claim is its own atomic act outside any producer transaction. One wide port would have handed producers claim methods they must never call, and would have forced the future SQL adapter to reconcile two transaction models behind one interface.

The envelope stays generic (`payload: dict`). The concrete `NoteApprovedPayload` lives in `domain/capture/`, the context that produces it, and serializes to dict at append time — so `domain/shared/outbox` never becomes a registry of every event schema. Schema drift is handled by minting a new `type`, not by mutating a payload shape in place.

**Redraft as a branch, not a mode.** A turn where `session.note_id` is already set reconciles the incoming chunks against the existing `Note` rather than creating one: `change_topic`, then tags reconciled to the turn's set through `remove_tag`/`add_tag`, then `update_content`. The turn's chunk sequence is authoritative for the whole draft — the model re-emits the complete shape each time, which is what the existing port contract already produces. The user never edits text directly, and there is no second endpoint.

**Approval as an explicit act, and the worker behind it.** `/approve` is intercepted by the TUI and turned into `POST /capture-sessions/{id}/approval`, so no model judgment stands between the user's intent and an irreversible write — the PRD's "nothing without explicit approval" guardrail becomes a property of the transport rather than a hope about the prompt. The handler calls `session.approve(note)` (which approves the note and closes the session in one domain act), loads the topic and tags, appends the envelope, and commits — all one transaction. The worker is an `asyncio.Task` started in a FastAPI lifespan: one process, no broker, matching the deployment constraint. Its `run_once()` is the whole unit of work and is public precisely so tests drive it directly, with no sleeping and no task scheduling.

## Critical Implementation Details

`OutboxEnvelope.fail(max_attempts)` decides between returning to `pending` and settling on `failed`; the worker passes the configured limit and the claimer only persists the result. Putting the retry cut-off in the domain method rather than in the worker loop is what keeps `attempts` meaningful under any future adapter — a SQL claimer inherits the policy instead of reimplementing it.

The in-memory `claim` must hold a single `asyncio.Lock` across read-select-and-mutate. Two concurrent `run_once()` calls awaiting the same store is exactly the scenario this slice claims to support, and without the lock the interleaving hands both workers the same envelope. This mirrors `SELECT ... FOR UPDATE SKIP LOCKED`, so the contract test survives the move to SQL unchanged.

---

## Phase 1: Outbox model and ports — stubs

### Overview

Materializes the shared outbox package and capture's payload type as importable symbols with unimplemented bodies. No behavior.

### Changes Required:

#### 1. Shared outbox package

**File**: `backend/src/domain/shared/__init__.py`, `backend/src/domain/shared/outbox/__init__.py`

**Intent**: Open the `domain/shared/` bucket the duck session settled on, with `outbox` as its first sub-package.

**Contract**: Empty package markers.

#### 2. Envelope model

**File**: `backend/src/domain/shared/outbox/model.py`

**Intent**: The generic envelope every producing context enqueues, with its status lifecycle expressed as domain methods rather than adapter-side field writes.

**Contract**: Exports `EnvelopeStatus`, `EnvelopeId`, `OutboxEnvelope`.

```python
class EnvelopeStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    CONSUMED = "consumed"
    FAILED = "failed"


class EnvelopeId(BaseModel, frozen=True):
    value: UUID

    @classmethod
    def new(cls) -> "EnvelopeId": ...


class OutboxEnvelope(BaseModel):
    id: EnvelopeId
    type: str
    payload: dict[str, object]
    status: EnvelopeStatus
    attempts: int
    created_at: datetime
    claimed_at: datetime | None
    claimed_by: str | None

    @classmethod
    def pending(cls, type: str, payload: dict[str, object]) -> "OutboxEnvelope": ...
    def claim(self, worker_id: str) -> None: ...      # pending -> processing, attempts += 1
    def consume(self) -> None: ...                    # processing -> consumed
    def fail(self, max_attempts: int) -> None: ...    # processing -> pending | failed
```

#### 3. Outbox exceptions

**File**: `backend/src/domain/shared/outbox/exceptions.py`

**Intent**: Illegal status transitions raise rather than silently corrupt the lifecycle.

**Contract**: `EnvelopeNotPendingError`, `EnvelopeNotProcessingError`, both `CoreException` subclasses, codes `envelope_not_pending` / `envelope_not_processing`.

#### 4. Role-split ports

**File**: `backend/src/domain/shared/outbox/ports.py`

**Intent**: Producer and consumer get separate contracts, because their transaction stories differ.

**Contract**:

```python
class OutboxAppender(Protocol):
    async def append(self, envelope: OutboxEnvelope) -> None: ...


class OutboxClaimer(Protocol):
    async def claim(
        self, envelope_type: str, limit: int, worker_id: str
    ) -> list[OutboxEnvelope]: ...
    async def ack(self, envelope: OutboxEnvelope) -> None: ...
    async def fail(self, envelope: OutboxEnvelope) -> None: ...
```

#### 5. Capture's payload

**File**: `backend/src/domain/capture/outbox.py`

**Intent**: The `note_approved` payload is a denormalized snapshot owned by capture, so a consumer never reaches back into capture's repositories to resolve labels.

**Contract**: Exports `NOTE_APPROVED: str`, `VocabularySnapshot`, `NoteApprovedPayload` with `of(note, topic, tags)` and `to_envelope()`.

```python
NOTE_APPROVED = "note_approved"


class VocabularySnapshot(BaseModel, frozen=True):
    id: UUID
    label: str


class NoteApprovedPayload(BaseModel, frozen=True):
    note_id: UUID
    session_id: UUID
    topic: VocabularySnapshot
    content: str
    tags: list[VocabularySnapshot]
    approved_at: datetime

    @classmethod
    def of(cls, note: Note, topic: Topic, tags: list[Tag]) -> "NoteApprovedPayload": ...
    def to_envelope(self) -> OutboxEnvelope: ...
```

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run ruff check src` passes
- `cd backend && uv run basedpyright` reports no new errors
- `cd backend && uv run python -c "from domain.shared.outbox.model import OutboxEnvelope; from domain.shared.outbox.ports import OutboxAppender, OutboxClaimer; from domain.capture.outbox import NoteApprovedPayload"` exits 0

---

## Phase 2: Outbox model and ports — behavior

### Overview

The envelope's status lifecycle and the payload snapshot become real.

### Changes Required:

#### 1. Envelope transitions

**File**: `backend/src/domain/shared/outbox/model.py`

**Intent**: Make the lifecycle total and guarded, with the retry cut-off owned by the domain so any adapter inherits it.

**Contract**: `pending()` builds status `PENDING`, `attempts=0`, `created_at=now(UTC)`, null claim fields. `claim(worker_id)` requires `PENDING`, else raises `EnvelopeNotPendingError`; sets `PROCESSING`, `claimed_by`, `claimed_at=now(UTC)`, `attempts += 1`. `consume()` requires `PROCESSING`, else `EnvelopeNotProcessingError`; sets `CONSUMED`. `fail(max_attempts)` requires `PROCESSING`; sets `PENDING` and clears `claimed_at`/`claimed_by` when `attempts < max_attempts`, otherwise sets `FAILED`.

#### 2. Payload snapshot

**File**: `backend/src/domain/capture/outbox.py`

**Intent**: Freeze labels at approval time.

**Contract**: `of(note, topic, tags)` reads `note.id.value`, `note.session_id.value`, `note.content.value`, `note.approved_at`, and builds `VocabularySnapshot` from each `Topic`/`Tag`'s `id.value` and `label.value`. `to_envelope()` returns `OutboxEnvelope.pending(NOTE_APPROVED, self.model_dump(mode="json"))`.

#### 3. Error mapping entries

**File**: `backend/src/adapters/http/errors.py`

**Intent**: Keep the exhaustiveness test green.

**Contract**: `"envelope_not_pending": 409`, `"envelope_not_processing": 409`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/shared/test_outbox_model.py tests/unit/capture/test_note_approved_payload.py -v` passes
- `cd backend && uv run pytest tests/unit/test_http_error_mapping.py -v` passes
- `cd backend && uv run pytest` passes

---

## Phase 3: In-memory outbox adapters and UnitOfWork — stubs

### Overview

Materializes the in-memory store and both adapters, and widens `UnitOfWork` with its sixth member.

### Changes Required:

#### 1. Shared in-memory package

**File**: `backend/src/adapters/out/in_memory/shared/__init__.py`, `backend/src/adapters/out/in_memory/shared/outbox/__init__.py`

**Intent**: Mirror the domain package layout on the adapter side.

**Contract**: Empty package markers.

#### 2. Store and adapters

**File**: `backend/src/adapters/out/in_memory/shared/outbox/store.py`, `.../appender.py`, `.../claimer.py`

**Intent**: One store shared by both adapters, matching the existing `InMemoryMessageStore` pattern where a store backs several collaborators.

**Contract**:

```python
class InMemoryOutboxStore:
    def __init__(self) -> None: ...
    def snapshot(self) -> dict[UUID, OutboxEnvelope]: ...
    def restore(self, snapshot: dict[UUID, OutboxEnvelope]) -> None: ...
    async def put(self, envelope: OutboxEnvelope) -> None: ...
    async def select_pending(self, envelope_type: str, limit: int) -> list[OutboxEnvelope]: ...
    def lock(self) -> asyncio.Lock: ...
    def all(self) -> list[OutboxEnvelope]: ...


class InMemoryOutboxAppender:
    def __init__(self, store: InMemoryOutboxStore) -> None: ...
    async def append(self, envelope: OutboxEnvelope) -> None: ...


class InMemoryOutboxClaimer:
    def __init__(self, store: InMemoryOutboxStore) -> None: ...
    async def claim(self, envelope_type: str, limit: int, worker_id: str) -> list[OutboxEnvelope]: ...
    async def ack(self, envelope: OutboxEnvelope) -> None: ...
    async def fail(self, envelope: OutboxEnvelope) -> None: ...
```

#### 3. UnitOfWork gains `outbox`

**File**: `backend/src/application/capture/ports.py`

**Intent**: Enqueue is a member of the producer's own transaction, per the duck session.

**Contract**: `UnitOfWork` Protocol adds `outbox: OutboxAppender`.

#### 4. InMemoryUnitOfWork joins the snapshot set

**File**: `backend/src/adapters/out/in_memory/capture/unit_of_work.py`

**Intent**: A repository outside the snapshot set silently loses rollback.

**Contract**: Constructor takes `outbox_store: InMemoryOutboxStore` and `outbox: InMemoryOutboxAppender`; `__aenter__` snapshots the outbox store; `__aexit__` restores it when `commit()` never ran.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run ruff check src` passes
- `cd backend && uv run basedpyright` reports no new errors

---

## Phase 4: In-memory outbox adapters and UnitOfWork — behavior

### Overview

The contract both ports must satisfy, including the atomicity two parallel workers depend on.

### Changes Required:

#### 1. Appender and transactional membership

**File**: `backend/src/adapters/out/in_memory/shared/outbox/appender.py`, `.../store.py`

**Intent**: An envelope appended in a turn that rolls back must not survive.

**Contract**: `append()` writes the envelope into the store keyed by `envelope.id.value`. `InMemoryUnitOfWork` snapshot/restore covers it, so an uncommitted `async with uow` block leaves the store as it was.

#### 2. Atomic claim

**File**: `backend/src/adapters/out/in_memory/shared/outbox/claimer.py`

**Intent**: Two workers polling the same store never receive the same envelope.

**Contract**: `claim()` holds the store's single `asyncio.Lock` across select-and-mutate: selects up to `limit` `PENDING` envelopes of the given `type` in `created_at` order, calls `envelope.claim(worker_id)` on each, writes them back, releases the lock, returns them. `ack()` calls nothing itself — the caller has already invoked `consume()`/`fail(...)` — and persists the envelope. `fail()` persists likewise.

#### 3. Contract test suite

**File**: `backend/tests/unit/shared/test_outbox_contract.py`

**Intent**: One behavioral contract per port, parametrized over implementations, per the contract-testing rule.

**Contract**: Covers append-then-visible, rollback-then-absent, claim filters by `type`, claim respects `limit`, a claimed envelope is invisible to a second claim, `asyncio.gather` of two claims returns disjoint sets, ack settles `CONSUMED`, fail below the limit returns to `PENDING` and above it settles `FAILED`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/shared -v` passes
- `cd backend && uv run pytest tests/unit/capture/test_unit_of_work.py -v` passes
- `cd backend && uv run pytest` passes

---

## Phase 5: Capture domain approval and mutators — stubs

### Overview

Materializes the operations the ADR assigns to `Note` and `CaptureSession` but S-04 deliberately left out.

### Changes Required:

#### 1. Note operations

**File**: `backend/src/domain/capture/note.py`

**Intent**: The redraft loop and the one-way approval transition, as the ADR specifies them.

**Contract**:

```python
def update_content(self, content: NoteContent) -> None: ...
def change_topic(self, topic: Topic) -> None: ...
def add_tag(self, tag: Tag) -> None: ...
def remove_tag(self, tag: Tag) -> None: ...
def approve(self, session_id: SessionId) -> None: ...
```

#### 2. Session terminal transition

**File**: `backend/src/domain/capture/capture_session.py`

**Intent**: "Approval always closes the session" is one domain act, provable without repositories.

**Contract**: `def approve(self, note: Note) -> None: ...` and `def close(self) -> None: ...`.

#### 3. New exceptions

**File**: `backend/src/domain/capture/exceptions.py`

**Intent**: Guards raise rather than silently no-op.

**Contract**: `NoteNotDraftError`, `NoteSessionMismatchError`, `SessionNoteMissingError`, `NoteNotFoundError`, `TagNotOnNoteError` — all `CoreException` subclasses.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run ruff check src` passes
- `cd backend && uv run basedpyright` reports no new errors

---

## Phase 6: Capture domain approval and mutators — behavior

### Overview

The guards and transitions become real and are proven against pure objects.

### Changes Required:

#### 1. Draft-only mutators

**File**: `backend/src/domain/capture/note.py`

**Intent**: A note that has left `draft` is immutable.

**Contract**: All four mutators raise `NoteNotDraftError` unless `status == NoteStatus.DRAFT`. `change_topic` sets `topic_id` from the passed `Topic`. `add_tag` appends `tag.id`, ignoring a duplicate. `remove_tag` drops `tag.id`, raising `TagNotOnNoteError` when absent.

#### 2. One-way approval

**File**: `backend/src/domain/capture/note.py`

**Intent**: Approval is irreversible and cannot be applied across aggregates by mistake.

**Contract**: `approve(session_id)` raises `NoteSessionMismatchError` when `session_id != self.session_id`, raises `NoteNotDraftError` unless status is `DRAFT`, then sets `status = APPROVED` and `approved_at = now(UTC)`.

#### 3. Session approval closes the session

**File**: `backend/src/domain/capture/capture_session.py`

**Intent**: AC-15 as one assertion on a pure object.

**Contract**: `approve(note)` raises `CaptureSessionClosedError` unless status is `OPEN`, raises `SessionNoteMissingError` when `self.note_id` is None or does not equal `note.id`, then calls `note.approve(self.id)` and `self.close()`. `close()` raises `CaptureSessionClosedError` when already closed, else sets `status = CLOSED`.

#### 4. Error mapping entries

**File**: `backend/src/adapters/http/errors.py`

**Intent**: Exhaustiveness.

**Contract**: `note_not_draft`: 409, `note_session_mismatch`: 409, `session_note_missing`: 409, `note_not_found`: 404, `tag_not_on_note`: 409.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/test_model.py -v` passes
- `cd backend && uv run pytest tests/unit/test_http_error_mapping.py -v` passes
- `cd backend && uv run pytest` passes

---

## Phase 7: Redraft and approval command — stubs

### Overview

Materializes the approval command and the redraft branch's signature surface.

### Changes Required:

#### 1. Approval command

**File**: `backend/src/application/capture/commands/approve_note.py`

**Intent**: The command handler that owns the approve-and-enqueue transaction, per the ADR.

**Contract**:

```python
class ApproveNoteCommand:
    def __init__(self, uow: UnitOfWork) -> None: ...
    async def handle(self, session_id: SessionId) -> ApproveNoteResponseDTO: ...
```

#### 2. Response DTO

**File**: `backend/src/application/capture/dto.py`

**Intent**: What the client renders as the confirmation.

**Contract**: `ApproveNoteResponseDTO(note_id: UUID, topic: str, tags: list[str], approved_at: datetime)`.

#### 3. Redraft seam

**File**: `backend/src/application/capture/commands/send_message.py`

**Intent**: Name the branch before it does anything, so tests import a real symbol.

**Contract**: Private `async def _apply_redraft(self, uow, note, topic, tags, content) -> None` with an unimplemented body, called from `handle()` only when `session.note_id is not None`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run ruff check src` passes
- `cd backend && uv run basedpyright` reports no new errors

---

## Phase 8: Redraft and approval command — behavior

### Overview

The redraft branch mutates in place, and approval writes note, session and envelope in one transaction.

### Changes Required:

#### 1. Redraft branch

**File**: `backend/src/application/capture/commands/send_message.py`

**Intent**: A second drafting turn reshapes the existing note instead of failing.

**Contract**: When `session.note_id` is set and the turn produced draft chunks, load the note via `uow.notes.get(...)` (raise `NoteNotFoundError` when absent), call `change_topic(resolved_topic)`, reconcile tags to the turn's resolved set through `remove_tag` for dropped ids and `add_tag` for added ones, call `update_content(NoteContent(value=draft_text))`, then `uow.notes.add(note)`. `session.draft_note(...)` is not called and `CaptureSession` is not re-saved. The turn still emits `draft_topic`/`draft_tag`/`draft_delta` and a `draft_done` carrying the same `note_id` as the first draft.

#### 2. Approval handler

**File**: `backend/src/application/capture/commands/approve_note.py`

**Intent**: One transaction covering the note, the session and the envelope — AC-14 and AC-15.

**Contract**: Inside `async with self._uow as uow`: load the session (`CaptureSessionNotFoundError`), raise `SessionNoteMissingError` when `note_id` is None, load the note (`NoteNotFoundError`), call `session.approve(note)`, `uow.notes.add(note)`, `uow.capture_sessions.save(session)`, load `Topic` from `uow.topics` and each `Tag` from `uow.tags`, build `NoteApprovedPayload.of(...)`, `await uow.outbox.append(payload.to_envelope())`, then `commit()`. The DTO is built inside the block and returned after it. Any raise leaves zero envelopes, because the whole block rolls back.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/test_send_message_command.py tests/unit/capture/test_approve_note_command.py -v` passes
- `cd backend && uv run pytest` passes

---

## Phase 9: Outbox worker — stubs

### Overview

Materializes the handler protocol, the worker, and the placeholder note-save handler.

### Changes Required:

#### 1. Handler protocol

**File**: `backend/src/application/shared/__init__.py`, `backend/src/application/shared/outbox/__init__.py`, `backend/src/application/shared/outbox/ports.py`

**Intent**: The extension point `distill` later fills.

**Contract**:

```python
class OutboxHandler(Protocol):
    envelope_type: str

    async def handle(self, envelope: OutboxEnvelope) -> None: ...
```

#### 2. Worker

**File**: `backend/src/adapters/out/worker/__init__.py`, `backend/src/adapters/out/worker/outbox_worker.py`

**Intent**: One polling loop in the API's own event loop, with the unit of work exposed for tests.

**Contract**:

```python
class OutboxWorker:
    def __init__(
        self,
        claimer: OutboxClaimer,
        handlers: Sequence[OutboxHandler],
        worker_id: str,
        batch_size: int,
        max_attempts: int,
    ) -> None: ...

    async def run_once(self) -> int: ...
    async def run_forever(self, interval_seconds: float) -> None: ...
```

#### 3. Placeholder handler

**File**: `backend/src/adapters/out/worker/handlers/note_save.py`

**Intent**: Prove the chain end to end; deliberately trivial and expected to be replaced by `distill`.

**Contract**: `LoggingNoteSaveHandler` with `envelope_type = NOTE_APPROVED` and a `handle()` that validates the payload into `NoteApprovedPayload` and logs one INFO line.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run ruff check src` passes
- `cd backend && uv run basedpyright` reports no new errors

---

## Phase 10: Outbox worker — behavior

### Overview

The claim → handle → ack chain, the retry policy, and the parallel-safety property.

### Changes Required:

#### 1. Single pass

**File**: `backend/src/adapters/out/worker/outbox_worker.py`

**Intent**: `run_once()` is the whole unit of work, so tests never sleep or schedule tasks.

**Contract**: For each registered handler, `claim(handler.envelope_type, batch_size, worker_id)`; for each claimed envelope call `handler.handle(envelope)`, then `envelope.consume()` and `claimer.ack(envelope)`. On any exception from `handle`, call `envelope.fail(max_attempts)` and `claimer.fail(envelope)`, log WARNING below the cut-off and ERROR at it, and continue with the next envelope. Returns the count of envelopes acked.

#### 2. Continuous loop

**File**: `backend/src/adapters/out/worker/outbox_worker.py`

**Intent**: A worker sharing the API's process must never take the process down.

**Contract**: `run_forever(interval_seconds)` loops `run_once()` then `asyncio.sleep(interval_seconds)`, catching and logging every exception except `asyncio.CancelledError`, which propagates so lifespan shutdown can cancel the task.

#### 3. Worker tests

**File**: `backend/tests/unit/shared/test_outbox_worker.py`

**Intent**: Prove dispatch, retry and parallel safety without I/O.

**Contract**: A handler raising once is retried on the next `run_once()` and succeeds; a handler raising `max_attempts` times leaves the envelope `FAILED`; an envelope whose `type` no handler claims stays `PENDING`; two `OutboxWorker`s with distinct `worker_id`s driven through `asyncio.gather` over the same claimer process disjoint envelope sets and each envelope exactly once.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/shared/test_outbox_worker.py -v` passes
- `cd backend && uv run pytest` passes

---

## Phase 11: HTTP surface and settings — stubs

### Overview

Materializes the approval route, the private outbox route, its query side, and the configuration the worker and the environment gate read.

### Changes Required:

#### 1. Environment and worker settings

**File**: `backend/src/config/settings.py`

**Intent**: One discriminator gates the private route; the rest tunes the worker.

**Contract**:

```python
class Environment(StrEnum):
    LOCAL = "local"
    STAGING = "staging"
    PROD = "prod"


# on Settings:
environment_name: Environment = Environment.LOCAL
outbox_poll_interval_seconds: float = 1.0
outbox_batch_size: int = 10
outbox_max_attempts: int = 3
outbox_worker_id: str = "note-save-worker"
```

#### 2. Approval route

**File**: `backend/src/adapters/http/capture.py`

**Intent**: The explicit, deterministic approval act.

**Contract**: `POST /capture-sessions/{session_id}/approval` returning `ApproveNoteResponseDTO`, taking `ApproveNoteCommand` through `Depends(get_approve_note_command)`.

#### 3. Private outbox route and its query

**File**: `backend/src/adapters/http/outbox.py`, `backend/src/application/shared/outbox/dto.py`, `backend/src/application/shared/outbox/queries/envelopes.py`, `backend/src/adapters/out/in_memory/shared/outbox/envelope_query.py`

**Intent**: An ops/debug view of the queue that never exists in production. Read side follows CQRS-lite: a query handler reading straight into a DTO, with no `UnitOfWork`.

**Contract**: `OutboxEnvelopeDTO(id, type, status, attempts, created_at, claimed_at, claimed_by)`; `OutboxEnvelopeQueryPort.list_envelopes() -> list[OutboxEnvelopeDTO]`; `InMemoryOutboxEnvelopeQueryAdapter` over `InMemoryOutboxStore`; router exposing `GET /_outbox`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run ruff check src` passes
- `cd backend && uv run basedpyright` reports no new errors

---

## Phase 12: HTTP surface and settings — behavior

### Overview

The endpoints' status codes, shapes and gating.

### Changes Required:

#### 1. Approval endpoint contract

**File**: `backend/src/adapters/http/capture.py`

**Intent**: The transport-level guarantee behind AC-14.

**Contract**: 200 with the DTO on success; 404 `capture_session_not_found` for an unknown session; 409 `session_note_missing` when no draft exists; 409 `capture_session_closed` on a second approval. Errors travel through the existing `core_exception_handler`, so the body is `{code, detail}`.

#### 2. Environment gating

**File**: `backend/src/main.py`

**Intent**: On production the route does not exist, rather than existing and being undocumented.

**Contract**: The `/_outbox` router is included only when `settings.environment_name != Environment.PROD`. Outside production it is a normal documented route and appears in `/openapi.json`. On production, `GET /_outbox` is 404.

#### 3. Integration tests

**File**: `backend/tests/integration/test_capture_http.py`, `backend/tests/integration/test_outbox_http.py`

**Intent**: Prove both contracts through the real app.

**Contract**: Approval happy path plus all three error codes; `/_outbox` lists an appended envelope and reflects its status after a `run_once()`; an app built with `environment_name=prod` returns 404 for `/_outbox` and omits it from `/openapi.json`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/integration -v` passes
- `cd backend && uv run pytest` passes

---

## Phase 13: Composition and worker lifecycle

### Overview

Wiring: the single outbox store, the worker, and the lifespan task that runs it beside the API. Not TDD'able — this is composition-root and process-lifecycle configuration whose behavior is already covered by the phases above.

### Changes Required:

#### 1. Composition root

**File**: `backend/src/adapters/compose.py`

**Intent**: One store instance behind both the appender and the claimer, or the worker polls a queue nothing writes to.

**Contract**: Module-level `_outbox_store`, `_outbox_appender`, `_outbox_claimer`, `_outbox_query`, `_note_save_handler`, `_outbox_worker`. `_unit_of_work()` passes the store and appender to `InMemoryUnitOfWork`. Adds `get_approve_note_command()` and `get_outbox_envelope_query()`; exports `get_outbox_worker()`.

#### 2. Lifespan task

**File**: `backend/src/main.py`

**Intent**: One process, no broker — the deployment constraint from `overview-thougts`.

**Contract**: An `asynccontextmanager` lifespan creates `asyncio.create_task(worker.run_forever(settings.outbox_poll_interval_seconds))` on startup and cancels it — awaiting the `CancelledError` — on shutdown. Passed as `FastAPI(lifespan=...)`.

#### 3. Worker logging

**File**: `backend/src/adapters/out/worker/outbox_worker.py`, `backend/src/adapters/out/worker/handlers/note_save.py`

**Intent**: The only way to see the worker working during manual verification.

**Contract**: `logging.getLogger(__name__)`; INFO on claim and ack, WARNING on a retryable failure, ERROR on the dead-letter transition. No logging in domain or application code.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest` passes
- `cd backend && uv run ruff check src` passes

#### Manual Verification:
- `cd backend && uv run fastapi dev src/main.py` starts and the log shows no worker error while idle
- With the server running, `curl http://localhost:8000/_outbox` returns `[]`

---

## Phase 14: TUI approval — stubs

### Overview

Materializes the client call, the store action and the state field the screen reads.

### Changes Required:

#### 1. Regenerate the API schema

**File**: `tui/src/api/generated/schema.d.ts`

**Intent**: The approval endpoint is plain JSON, so unlike the SSE route it goes through the generated client.

**Contract**: Regenerated with `pnpm generate:api` against a running backend; includes `/capture-sessions/{session_id}/approval` and, because the local environment is not production, `/_outbox` — which the TUI never calls.

#### 2. Client function

**File**: `tui/src/api/stream.ts`

**Intent**: One typed call for approval.

**Contract**: `export async function approveNote(sessionId: string): Promise<{ noteId: string; topic: string; tags: string[] }>`, throwing `SendMessageHttpError` on a `{code, detail}` body.

#### 3. Store surface

**File**: `tui/src/store/chat.ts`

**Intent**: Approval is terminal state the screen can render off.

**Contract**: `ChatState` gains `approved: boolean` (initially `false`); `ChatActions` gains `approveDraft: () => Promise<void>`.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm typecheck` passes
- `cd tui && pnpm lint` passes

---

## Phase 15: TUI approval — behavior

### Overview

`/approve` is intercepted deterministically, and the screen ends on a confirmation.

### Changes Required:

#### 1. Command interception

**File**: `tui/src/screens/CaptureScreen.tsx`

**Intent**: The approval gesture never travels as a conversational turn, so no model judgment sits between intent and write.

**Contract**: `handleSubmit` compares the trimmed input to the exact literal `/approve`; on a match it calls `approveDraft()` and sends no message. Anything else, including near-misses, goes to `sendUserMessage` as before.

#### 2. Approval action

**File**: `tui/src/store/chat.ts`

**Intent**: Guard locally, then commit.

**Contract**: `approveDraft()` returns early with a `streamError` of code `no_draft_to_approve` when `draft?.noteId` is null — nothing leaves the client. Otherwise it calls `approveNote(sessionId)` and on success sets `approved: true`, clearing `streamError`. A `SendMessageHttpError` populates `streamError` and leaves `approved` false, so the user can retry.

#### 3. Terminal render

**File**: `tui/src/screens/CaptureScreen.tsx`

**Intent**: AC-15's "the session ends" is visible, and a closed session cannot be typed into.

**Contract**: When `approved` is true the draft panel is replaced by `✓ Approved — queued for saving` and `TextInput` receives `focus={false}` permanently. The row-budget heuristic in `shouldShowWelesBrand` accounts for the confirmation block the same way it accounts for the draft block.

#### 4. Tests

**File**: `tui/test/chat.test.ts`, `tui/test/captureScreen.test.tsx`

**Intent**: Prove the interception and the terminal state.

**Contract**: `/approve` with a ready draft calls the endpoint and sets `approved`; `/approve` with no draft makes no request; a message containing the word "approve" in prose is sent as a normal turn; the screen renders the confirmation and stops accepting input.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm test` passes
- `cd tui && pnpm typecheck && pnpm lint` pass

#### Manual Verification:
- Start the backend, run `cd tui && pnpm build && pnpm start`, hold a short conversation, type `we're done`, then type a change request and confirm the draft panel updates while `note_id` stays the same
- Type `/approve` and confirm the panel is replaced by the confirmation, the input stops accepting text, and the backend log shows the worker claiming and handling the envelope

---

## Phase 16: Acceptance scenarios for US-06 and US-07

### Overview

Gherkin coverage for AC-12–AC-15. This phase authors tests, so it does not go through `/unit-test`.

### Changes Required:

#### 1. Marker registration

**File**: `backend/pyproject.toml`

**Intent**: `AC-12`–`AC-15` are undeclared markers today, so `-m` filtering silently matches nothing.

**Contract**: Four entries appended to `[tool.pytest.ini_options] markers`.

#### 2. Feature files

**File**: `backend/tests/features/capture-flow/US-06-reshape-draft.feature`, `backend/tests/features/capture-flow/US-07-approve-to-outbox.feature`

**Intent**: The two stories this slice realizes, tagged per the existing convention.

**Contract**: US-06 covers AC-12 (the draft's topic, body and tags are shown before anything is saved) and AC-13 (a described change yields a redraft on the same note, with no direct text editing). US-07 covers AC-14 (no envelope exists before approval) and AC-15 (approval enqueues the envelope and closes the session). Tags: `@capture-flow` plus the AC id.

#### 3. Step definitions

**File**: `backend/tests/bdd/steps/approve_outbox.py`, `backend/tests/bdd/test_features.py`

**Intent**: Steps drive the real application through its HTTP surface.

**Contract**: New step module registered in `pytest_plugins`; steps reuse `tests/integration/support/in_memory_capture.py` where it fits.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/bdd -v` passes
- `cd backend && uv run pytest tests/bdd -m "capture-flow and AC-14" -v` selects at least one scenario
- `cd backend && uv run pytest` passes

#### Manual Verification:
- `cd backend && uv run pytest tests/bdd --collect-only` lists the new scenarios with no undefined steps

---

## Testing Strategy

### Unit Tests:

`OutboxEnvelope`'s transition table including every illegal transition; `NoteApprovedPayload.of()` snapshotting labels rather than ids; `Note`'s four mutators and `approve()` under the draft-only and session-match guards; `CaptureSession.approve()` closing the session in one act; the redraft branch reconciling tags to the turn's set; `ApproveNoteCommand` writing note, session and envelope in one transaction and leaving nothing behind on failure; `OutboxWorker`'s dispatch, retry and dead-letter behavior.

### Integration Tests:

One behavioral contract suite for `OutboxAppender` and `OutboxClaimer`, parametrized over implementations — in-memory runs on every CI invocation. HTTP tests for the approval endpoint's four outcomes and for `/_outbox`'s presence, content and production absence.

### Manual Testing Steps:

1. `cd backend && uv run fastapi dev src/main.py`
2. `cd tui && pnpm build && pnpm start`
3. Converse, then type `we're done` — the draft panel fills.
4. Type a change request in plain language — the panel updates and `note_id` is unchanged.
5. Type `/approve` — the panel is replaced by the confirmation and input stops accepting text.
6. Watch the backend console for the worker's claim and handle lines.
7. `curl http://localhost:8000/_outbox` — the envelope reads `consumed`.

## Performance Considerations

The worker polls on a fixed interval with no backoff, so an idle system does constant small work — negligible at one user, and the interval is configurable. `claim()` serializes every consumer through one `asyncio.Lock`; with one worker and one handler there is no contention worth measuring, and the lock disappears when a SQL claimer takes over. Loading `Topic` and each `Tag` at approve time is N+1 by construction, bounded by the tag count of a single note and executed once per session.

## Migration Notes

**Lease and reclaim are deliberately absent.** An envelope claimed by a worker that then crashes stays `processing` forever, because nothing reclaims it. The duck session `outbox-shared` parked the claim algorithm until `distill` exists, and this slice unparks only the atomic-claim half. `claimed_at` and `claimed_by` are populated now specifically so a reclaim loop can be added later without touching the schema or the payload: the future change adds a clock port, a `lease_seconds` setting, and a select that also returns `processing` envelopes older than the lease. The contract test written in Phase 4 is the one that must grow a case at that point.

**The SQL adapter inherits the contract, not the code.** `claim()`'s in-memory lock exists to reproduce `SELECT ... FOR UPDATE SKIP LOCKED`; when the Postgres adapter lands it should be parametrized into the same contract suite rather than getting its own.

## References

- `context/efforts/capture-flow/prd.md` — FR-011–FR-014, guardrails
- `context/efforts/capture-flow/stories.md` — US-06 (AC-12, AC-13), US-07 (AC-14, AC-15)
- `context/efforts/capture-flow/roadmap.md` — slice S-06
- `context/adrs/capture-flow-domain-shape/decision.md` — aggregate operations, approval ownership, outbox write point
- `context/adrs/hexagonal-arch-shape/decision.md` — layering, CQRS-lite, InMemoryFirst, contract testing
- `context/duck-sessions/outbox-shared/log.md` — envelope shape, payload, UoW membership, parked claim algorithm
- `context/duck-sessions/overview-thougts/log.md` — single-loop worker topology, cheap-VPS constraint
- `context/archive/changes/2026-08-31-capture-flow-draft-note/plan.md` — the draft pipeline this slice extends
