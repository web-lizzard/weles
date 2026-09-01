# Drafted Note and Topic Implementation Plan

## Overview

Slice S-04 of the `capture-flow` effort. When the user signals in conversation that they are done, the agent stops asking questions and instead produces a draft note — a topic label, a set of tags, and a body — synthesized from the transcript, streamed into the TUI as it is generated and persisted as a `Note` aggregate. This realizes AC-08 (a draft note with topic, body and tags derived from the discussion) and AC-09 (the draft's topic may be more specific than the one the user originally named).

The slice is vertical: it adds three domain aggregates, extends the streaming port contract so a single stream can carry more than one kind of content, extends the SSE event vocabulary, and renders the incoming draft in the TUI.

Execution state for this plan lives in `todos.md`, sibling of this file.

## Current State Analysis

The capture flow already runs end to end for conversation: `POST /capture-sessions` opens a session, `POST /capture-sessions/{id}/messages` streams an agent reply over SSE, and the Ink TUI renders the transcript, the session topic and a coverage banner.

What exists:

- `CaptureSession` (`backend/src/domain/capture/capture_session.py:9`) — `id`, `topic: Topic | None`, `status`, `created_at`, with `start()` taking no topic and `assign_topic()` setting it later from the first user message.
- `Message` (`backend/src/domain/capture/message.py:13`) — immutable, append-only, already matching the ADR's decided shape.
- `Topic` (`backend/src/domain/capture/value_objects.py:27`) — a frozen string wrapper. This is the **session-level** topic the ADR describes, not the note-level aggregate.
- Ports: `CaptureSessionRepository`, `MessageRepository` (domain); `TopicExtractionPort`, `ConfidenceAssessmentPort`, `ReplyGenerationPort`, `UnitOfWork` (application); `TranscriptQueryPort` (query side).
- `GenerateReplyCommand` (`backend/src/application/capture/commands/send_message.py:26`) — one `UnitOfWork` per turn, streams `delta` events inside the block, constructs `ReplyDoneEvent` inside and yields it after `commit()`.
- SSE vocabulary: `ReplyDeltaEvent`, `ReplyDoneEvent`, `ReplyErrorEvent` under a `Field(discriminator="type")` union (`backend/src/application/capture/dto.py:37`).
- TUI: hand-declared mirror of the SSE types (`tui/src/api/stream.ts`), a zustand store accumulating `currentReply` (`tui/src/store/chat.ts`), and `CaptureScreen` with a row-budget heuristic that decides whether the brand header fits (`tui/src/screens/CaptureScreen.tsx:137`).

What is missing: `Note`, `Tag` and the note-level `Topic` aggregate do not exist anywhere; there is no embedding port; `UnitOfWork` carries only two repositories; `ReplyGenerationPort` yields bare `str`, so a stream cannot say what kind of content a chunk is.

Key constraints discovered:

- `CaptureSession` diverges from the ADR's `start(topic: str)` shape. S-01 shipped against the current shape and its acceptance scenarios are archived and green. This plan does not touch it — see "What We're NOT Doing".
- `Message.record()` builds `MessageContent`, which rejects empty strings. A turn that produced no reply text at all could therefore not record an agent message, which is why the port contract below requires every drafting turn to open with at least one `reply` chunk.
- `EXCEPTION_STATUS_MAP` (`backend/src/adapters/http/errors.py:6`) is guarded by an exhaustiveness test walking `CoreException.__subclasses__()`; every exception added here needs an entry.
- `tests/bdd/test_features.py:7` registers step modules explicitly in `pytest_plugins`; a new step module must be added there or its scenarios never load.

## Desired End State

A user talks through a topic, then writes something that reads as "we're done". In the same turn, without any new command or endpoint, the agent replies with a short hand-off line, then the TUI's draft panel fills in: first the topic heading, then tags appearing one by one, then the note body streaming in character by character. When the stream closes, a `Note` in status `draft` exists in storage, pointing at a freshly minted `Topic` and `Tag` rows that each carry an embedding, and `CaptureSession.note_id` names it.

Verify by running the backend and the TUI, holding a short conversation, and typing a confirmation phrase; the draft panel fills and the note is persisted. Automated verification is the AC-08/AC-09 acceptance scenarios plus the integration test asserting the SSE event sequence.

### Key Discoveries:

- The ADR uses the word "Topic" for two distinct facts and says so explicitly (`context/adrs/capture-flow-domain-shape/decision.md:28`, `:46`): the raw session label the user names at AC-01, and the reconciled note-level aggregate carrying an embedding. Python needs two names; this plan renames the value object to `SessionTopic` and gives the ADR's name to the aggregate.
- `status: closed` on `CaptureSession` means specifically "approved, note sent" (`decision.md:44`), not a generic terminal state — so the `status == open` guard on `draft_note()` is about not drafting a second note into an already-completed session, and is structurally unreachable until S-06 introduces `close()`.
- The redraft loop of AC-13 "mutates the single draft in place" through `Note`'s mutators (`decision.md:37`) — it does not re-enter `draft_note()`. Drafting and reshaping are two different operations on two different objects, which is what makes the one-note guard safe to add now.
- `GenerateReplyCommand.handle()` already models exactly the failure semantics this slice needs: stream inside the `UnitOfWork`, construct the terminal event inside, yield it after `commit()` (`send_message.py:80-88`). Nothing tells the client "saved" before the save happened.
- `InMemoryUnitOfWork` implements rollback by snapshot/restore over each store (`unit_of_work.py:31-40`); three new repositories must join that snapshot set or the rollback guarantee silently stops covering them.
- The existing `ReplyStreamEvent` union already establishes the `Literal[...]` + `Field(discriminator=...)` idiom (`dto.py:15-39`); the chunk union follows it rather than inventing a second convention.

## What We're NOT Doing

- **Reuse-or-mint reconciliation** (FR-009/FR-010, AC-10/AC-11). S-04 always mints a fresh `Topic` and `Tag`. `VocabularyResolver` is introduced as the seam S-05 rewrites in place; no similarity-search port is added.
- **Aligning `CaptureSession.start()` to the ADR's `start(topic: str)`.** The current `start()` + `assign_topic()` shape stays. This is a deliberate, recorded divergence: AC-08/AC-09 do not need it, and changing it would rewrite the entry-point behavior of two archived slices and the TUI's session-start UX. It remains open for a future change.
- **`Note` mutators, `approve()`, `close()`, and the outbox envelope** (AC-12–AC-15). All S-06.
- **A real LLM adapter with tool calls.** Per the InMemoryFirst rule, only the deterministic in-memory adapter is built; it simulates the model's mode switch with a confirmation-phrase rule.
- **Reading notes back.** No query handler, no DTO for listing drafts; the draft reaches the TUI through the stream and nowhere else.
- **A `discarded` transition.** `NoteStatus.DISCARDED` exists as the ADR's forward-looking extension point and nothing sets it.

## Implementation Approach

The trigger for drafting is conversational: the model decides, inside an ordinary turn, that the user has confirmed they are done, and switches what it emits. That decision reaches the application as a property of the stream rather than as a separate call, which is why `ReplyGenerationPort` is retyped from `AsyncIterator[str]` to `AsyncIterator[ReplyChunk]` — a discriminated union whose `kind` says whether a chunk is conversational reply text, a topic label, a tag label, or note body text.

The union is not a flat `{kind, text}` record, because the payload shapes genuinely differ: `topic` and `tag` carry whole, validated `Label` values, while `reply` and `note` carry raw fragments that by definition cannot satisfy a whole-value invariant. Encoding that in the type puts validation at the adapter boundary, where an LLM adapter parsing a tool call should do it.

Chunk order is part of the port's contract, not a convention: at least one `reply` chunk, then exactly one `topic`, then zero or more `tag`, then `note` chunks. The first `note` chunk implicitly closes the tag list, so no separate "tags complete" signal is needed. The contract test enforces all of it.

`GenerateReplyCommand` routes chunks. Reply text accumulates as today and becomes the agent `Message`. A `topic` or `tag` chunk goes to `VocabularyResolver`, which embeds the label, mints the aggregate, persists it through the `UnitOfWork`, and hands back the resolved object — and only then does the corresponding SSE event go out, carrying the resolved label rather than the model's proposal. Note text accumulates and becomes `NoteContent`. At end of stream the command calls `session.draft_note(topic, content, tags)`, saves the `Note` and the mutated session, commits, and only then yields `draft_done` followed by `done`.

Everything is one `UnitOfWork` per turn, so a failure mid-stream rolls the whole turn back and no partial note survives.

## Critical Implementation Details

Emitting `draft_topic` **after** the resolver, not straight from the chunk, is what makes this forward-compatible with S-05: once reuse lands, the label shown in the TUI must be the existing row's label, not the one the model proposed. Emitting early would make the heading rewrite itself mid-stream in the next slice.

The `status == open` guard on `draft_note()` cannot be reached through HTTP in this slice, because nothing closes a session until S-06. It is still implemented and unit-tested against a directly constructed closed session, because that is the invariant the ADR assigns to `CaptureSession`.

---

## Phase 1: Rename `Topic` to `SessionTopic`

### Overview

A pure, behavior-preserving rename that frees the name `Topic` for the aggregate the ADR describes. No new behavior; the existing green suites are the safety net.

### Changes Required:

#### 1. Domain value object and its exceptions

**File**: `backend/src/domain/capture/value_objects.py`, `backend/src/domain/capture/exceptions.py`

**Intent**: The string wrapper is the session-level label from AC-01, and once a note-level `Topic` aggregate exists the bare name becomes ambiguous at every call site.

**Contract**: `Topic` → `SessionTopic`; `TOPIC_MAX_LENGTH` → `SESSION_TOPIC_MAX_LENGTH`; `EmptyTopicError` → `EmptySessionTopicError`, `TopicTooLongError` → `SessionTopicTooLongError`. Field, validators and semantics unchanged.

#### 2. Consumers

**File**: `backend/src/domain/capture/capture_session.py`, `backend/src/application/capture/ports.py`, `backend/src/application/capture/commands/send_message.py`, `backend/src/adapters/out/in_memory/capture/topic_extraction.py`

**Intent**: Follow the rename through every reference so no alias or compatibility shim survives.

**Contract**: `CaptureSession.topic: SessionTopic | None`, `assign_topic(topic: SessionTopic)`, `TopicExtractionPort.extract(...) -> SessionTopic`.

#### 3. Error code mapping

**File**: `backend/src/adapters/http/errors.py`

**Intent**: Renaming a `CoreException` subclass silently changes its wire-visible `code`, and the exhaustiveness test fails if the table is not updated with it.

**Contract**: `EXCEPTION_STATUS_MAP` keys `empty_topic` → `empty_session_topic` and `topic_too_long` → `session_topic_too_long`, both still 422.

#### 4. Tests referencing the old name

**File**: `backend/tests/unit/capture/test_value_objects.py`, `backend/tests/unit/capture/test_model.py`, `backend/tests/unit/capture/test_send_message_command.py`, `backend/tests/unit/capture/contracts/test_topic_extraction_contract.py`, `backend/tests/bdd/steps/capture.py`, `backend/tests/bdd/steps/coverage_wrapup.py`

**Intent**: Keep every suite green through the rename; these are the proof the refactor changed nothing.

**Contract**: Imports and symbol references updated. No assertion changes.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest` green
- `cd backend && uv run ruff check src tests` clean
- `cd backend && uv run basedpyright` clean
- `cd backend && grep -rn "\bTopic\b" src/ | grep -v SessionTopic` returns no hits

---

## Phase 2: Domain vocabulary and aggregates — stubs

### Overview

Materializes every domain symbol the next phase's tests import: new value objects, the three aggregates, their repository ports, and the new exceptions. Signatures and fields only.

### Changes Required:

#### 1. New value objects

**File**: `backend/src/domain/capture/value_objects.py`

**Intent**: Give the aggregates their typed building blocks, following the frozen-`BaseModel` pattern the module already uses.

**Contract**: `NoteStatus(StrEnum)` with `DRAFT`/`APPROVED`/`DISCARDED`; `Label(BaseModel, frozen=True)` with `value: str`; `Embedding(BaseModel, frozen=True)` with `values: tuple[float, ...]`; `NoteContent(BaseModel, frozen=True)` with `value: str`; `NoteId`, `TopicId`, `TagId`, each frozen with `value: UUID` and a `new()` classmethod, matching `SessionId`. Constants `LABEL_MAX_LENGTH = 120`, `NOTE_CONTENT_MAX_LENGTH = 20000`. No validators yet.

#### 2. New exceptions

**File**: `backend/src/domain/capture/exceptions.py`

**Intent**: One exception per invariant the next phase enforces.

**Contract**: `EmptyLabelError`, `LabelTooLongError`, `EmptyEmbeddingError`, `EmptyNoteContentError`, `NoteContentTooLongError`, `SessionNoteAlreadyDraftedError`, all `CoreException` subclasses.

#### 3. `Topic` and `Tag` aggregates

**File**: `backend/src/domain/capture/topic.py`, `backend/src/domain/capture/tag.py`

**Intent**: The note-level, reconciled vocabulary the ADR requires. Structurally identical by decision, not by accident.

**Contract**: `Topic(BaseModel)` with `id: TopicId`, `label: Label`, `embedding: Embedding`, `created_at: datetime`, and `mint(cls, label: Label, embedding: Embedding) -> Topic` raising `NotImplementedError`. `Tag` identical with `TagId`.

#### 4. `Note` aggregate

**File**: `backend/src/domain/capture/note.py`

**Intent**: The draft itself, referencing its topic and tags by id per the reference-by-id rule while its factory takes resolved objects.

**Contract**:

```python
class Note(BaseModel):
    id: NoteId
    session_id: SessionId
    topic_id: TopicId
    content: NoteContent
    tag_ids: list[TagId]
    status: NoteStatus
    created_at: datetime
    approved_at: datetime | None

    @classmethod
    def draft(
        cls,
        session_id: SessionId,
        topic: Topic,
        content: NoteContent,
        tags: list[Tag],
    ) -> "Note": ...
```

#### 5. `CaptureSession` gains `note_id` and `draft_note()`

**File**: `backend/src/domain/capture/capture_session.py`

**Intent**: `draft_note()` is the sole entry point for note creation because "a note may only be drafted while the session is open" is knowledge only the session has; `note_id` is what makes "a session yields at most one note" an assertion on a pure object rather than a repository lookup. The field is a deliberate addition beyond the ADR's listed shape.

**Contract**: `note_id: NoteId | None`, set to `None` by `start()`. `draft_note(self, topic: Topic, content: NoteContent, tags: list[Tag]) -> Note` raising `NotImplementedError`.

#### 6. Repository ports

**File**: `backend/src/domain/capture/ports.py`

**Intent**: One port per aggregate root, kept to exactly what this slice uses. `get()` earns its place by making the contract tests and the acceptance scenarios able to assert what was persisted.

**Contract**: `NoteRepository` with `add(note: Note)` and `get(note_id: NoteId) -> Note | None`; `TopicRepository` and `TagRepository` with the same pair over their own types. No `find_similar` — that is S-05's addition.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest` green (existing suites unaffected)
- `cd backend && uv run basedpyright` clean
- `cd backend && uv run ruff check src tests` clean

### Review r4

Artifact: `reviews/2026-09-01-r4-impl-review.md`

- `R4-F2` — EXCEPTION_STATUS_MAP entries for Phase 3 landed one phase early
  Fix: a phase's commit touches only the files listed under that phase's own "Changes Required"; a later phase's contracted edit does not land early even when mechanically convenient — phase boundaries stay meaningful for review and bisection only if each phase's diff matches its own file list.

---

## Phase 3: Domain vocabulary and aggregates — behavior

### Overview

Implements the validators, the three factories, and the two guards on `draft_note()`.

### Changes Required:

#### 1. Value-object validation

**File**: `backend/src/domain/capture/value_objects.py`

**Intent**: Reject the values that would make an aggregate meaningless, following the trim-then-validate pattern already used by `SessionTopic` and `MessageContent`.

**Contract**: `Label` strips surrounding whitespace, raises `EmptyLabelError` when empty and `LabelTooLongError` beyond `LABEL_MAX_LENGTH`. `NoteContent` behaves the same with `EmptyNoteContentError` / `NoteContentTooLongError` and `NOTE_CONTENT_MAX_LENGTH`. `Embedding` raises `EmptyEmbeddingError` when `values` is empty.

#### 2. Factories

**File**: `backend/src/domain/capture/topic.py`, `backend/src/domain/capture/tag.py`, `backend/src/domain/capture/note.py`

**Intent**: Thin construct-with-validation, mirroring `Message.record()`.

**Contract**: `Topic.mint` / `Tag.mint` assign a new id and `datetime.now(UTC)`. `Note.draft` sets `status=NoteStatus.DRAFT`, `approved_at=None`, and extracts `topic_id=topic.id` and `tag_ids=[tag.id for tag in tags]` — storage holds ids, the operation took resolved objects.

#### 3. `CaptureSession.draft_note()`

**File**: `backend/src/domain/capture/capture_session.py`

**Intent**: Two disjoint guards. The first refuses to draft into a session that has already completed; the second enforces the PRD's "a session always yields at most one note" while the session is still open.

**Contract**: Raises `CaptureSessionClosedError` when `status != SessionStatus.OPEN`; raises `SessionNoteAlreadyDraftedError` when `note_id is not None`; otherwise delegates to `Note.draft(...)`, assigns `self.note_id = note.id`, and returns the note.

#### 4. Error code mapping

**File**: `backend/src/adapters/http/errors.py`

**Intent**: The exhaustiveness test requires every `CoreException` subclass to have a status.

**Contract**: `empty_label`, `label_too_long`, `empty_embedding`, `empty_note_content`, `note_content_too_long` → 422; `session_note_already_drafted` → 409.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit -v` green
- `cd backend && uv run pytest tests/unit/test_http_error_mapping.py -v` green
- `cd backend && uv run pytest` green

### Review r2

Artifact: `reviews/2026-09-01-r2-mutation-test-phase-3.md`

- `R2-F1` — core_exception_handler response must include detail equal to str(exc)
  Fix: assert `core_exception_handler` response JSON includes `detail` equal to `str(exc)`
- `R2-F2` — unmapped exception code falls back to HTTP 500
  Fix: assert `core_exception_handler` returns HTTP 500 when `exc.code()` is absent from `EXCEPTION_STATUS_MAP`

---

## Phase 4: Chunk protocol and SSE events — stubs

### Overview

Retypes the streaming port to carry marked chunks and extends the SSE vocabulary, keeping the existing conversation path working unchanged.

### Changes Required:

#### 1. The chunk union

**File**: `backend/src/application/capture/value_objects.py`

**Intent**: A single stream has to say what kind of content each chunk is. The payload shapes differ — whole validated labels versus raw fragments — so this is a discriminated union rather than a flat record.

**Contract**:

```python
class ReplyChunkKind(StrEnum):
    REPLY = "reply"
    TOPIC = "topic"
    TAG = "tag"
    NOTE = "note"


class ReplyTextChunk(BaseModel, frozen=True):
    kind: Literal[ReplyChunkKind.REPLY] = ReplyChunkKind.REPLY
    text: str


class DraftTopicChunk(BaseModel, frozen=True):
    kind: Literal[ReplyChunkKind.TOPIC] = ReplyChunkKind.TOPIC
    label: Label


class DraftTagChunk(BaseModel, frozen=True):
    kind: Literal[ReplyChunkKind.TAG] = ReplyChunkKind.TAG
    label: Label


class DraftContentChunk(BaseModel, frozen=True):
    kind: Literal[ReplyChunkKind.NOTE] = ReplyChunkKind.NOTE
    text: str


ReplyChunk = Annotated[
    ReplyTextChunk | DraftTopicChunk | DraftTagChunk | DraftContentChunk,
    Field(discriminator="kind"),
]
```

#### 2. Port changes

**File**: `backend/src/application/capture/ports.py`

**Intent**: The retyped generator, the new outbound embedding port, and the three repositories joining the commit boundary. `EmbeddingPort` sits in the application layer following the `TopicExtractionPort` precedent: it speaks domain vocabulary but is called by an application service, never by an aggregate.

**Contract**: `ReplyGenerationPort.generate(...) -> AsyncIterator[ReplyChunk]`. `EmbeddingPort` with `async def embed(self, text: str) -> Embedding`. `UnitOfWork` gains `notes: NoteRepository`, `topics: TopicRepository`, `tags: TagRepository`.

#### 3. SSE events

**File**: `backend/src/application/capture/dto.py`

**Intent**: Four new events. `draft_done` carries the full persisted value for the same reason `done` does — the client's accumulated buffer and what was actually stored can differ, and the stored value wins.

**Contract**: `DraftTopicEvent(type="draft_topic", label: str)`; `DraftTagEvent(type="draft_tag", label: str)`; `DraftDeltaEvent(type="draft_delta", text: str)`; `DraftDoneEvent(type="draft_done", note_id: UUID, topic: str, content: str, tags: list[str])`. All four join the `ReplyStreamEvent` union. `ReplyDoneEvent` is unchanged.

#### 4. Keep the existing path compiling

**File**: `backend/src/adapters/out/in_memory/capture/reply_generation.py`, `backend/src/application/capture/commands/send_message.py`, `backend/tests/unit/capture/contracts/test_reply_generation_contract.py`

**Intent**: The port's type change breaks its only adapter and its only consumer at once; both are brought forward with no behavior change.

**Contract**: The adapter wraps each slice of its reply in `ReplyTextChunk`. `GenerateReplyCommand` reads `chunk.text` for `ReplyTextChunk` and ignores other kinds for now. The contract test joins `chunk.text` instead of the raw string.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest` green
- `cd backend && uv run basedpyright` clean
- `cd backend && uv run pytest tests/bdd -m "capture-flow" -v` green (S-01/S-02 scenarios unaffected)

### Review r4

Artifact: `reviews/2026-09-01-r4-impl-review.md`

- `R4-F1` — Phase 3 pytest-green claim was false through Phase 8 (fix bundled into Phase 9)
  Fix: a phase's Automated rows are marked done only once that phase's own Success Criteria commands have actually been run and are green at that phase's own closing commit; a later phase's commit never silently absorbs an earlier phase's undelivered Contract.

---

## Phase 5: Deterministic draft adapter — behavior

### Overview

Teaches the in-memory adapter to switch modes on a confirmation phrase, and pins the stream's ordering rules into the port's contract test.

### Changes Required:

#### 1. Confirmation-phrase mode switch

**File**: `backend/src/adapters/out/in_memory/capture/reply_generation.py`

**Intent**: A real model decides to draft via a tool call; the in-memory adapter needs a deterministic stand-in so the whole flow is exercisable through HTTP without injecting test doubles.

**Contract**: A module-level closed set of confirmation phrases. When the last `MessageRole.USER` entry in the transcript matches one, the adapter emits, in order: one `ReplyTextChunk` hand-off line, exactly one `DraftTopicChunk` whose label is derived from the transcript, one `DraftTagChunk` per derived tag, then `DraftContentChunk` slices of a body synthesized from the transcript. Otherwise it emits `ReplyTextChunk`s exactly as before.

#### 2. Contract test covering kinds and ordering

**File**: `backend/tests/unit/capture/contracts/test_reply_generation_contract.py`

**Intent**: Order is part of this port's contract, not an adapter detail — the routing in `GenerateReplyCommand` and the "first `note` chunk closes the tag list" rule both depend on it, and any future LLM adapter must satisfy the same suite.

**Contract**: Parametrized over implementations, asserts for a drafting transcript: at least one `reply` chunk precedes everything; exactly one `topic` chunk; every `tag` chunk follows the `topic` chunk and precedes every `note` chunk; no `topic` or `tag` chunk appears after the first `note` chunk; joined `note` text is non-empty. For a non-drafting transcript, asserts every chunk is `reply`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/contracts/test_reply_generation_contract.py -v` green
- `cd backend && uv run pytest` green

---

## Phase 6: In-memory persistence and UnitOfWork — stubs

### Overview

Materializes the three repository adapters, the embedding adapter, and their place in the commit boundary and both composition roots.

### Changes Required:

#### 1. Repository adapters

**File**: `backend/src/adapters/out/in_memory/capture/note_repository.py`, `topic_repository.py`, `tag_repository.py`

**Intent**: Follow `InMemoryCaptureSessionRepository`, which owns its own dict and exposes `snapshot()`/`restore()` for the UnitOfWork rather than delegating to a shared store.

**Contract**: Each exposes `async add(...)`, `async get(...) -> ... | None`, `snapshot() -> dict[UUID, ...]`, `restore(snapshot)`.

#### 2. Embedding adapter

**File**: `backend/src/adapters/out/in_memory/capture/embedding.py`

**Intent**: An InMemoryFirst stand-in for the real embedding pipeline; deterministic so tests can assert equality.

**Contract**: `DeterministicEmbeddingAdapter` with `async def embed(self, text: str) -> Embedding` producing a fixed-dimension vector derived from the text. Same input always yields the same vector.

#### 3. UnitOfWork

**File**: `backend/src/adapters/out/in_memory/capture/unit_of_work.py`

**Intent**: The rollback guarantee has to cover the new aggregates, or a failure mid-draft would leave orphan topics and tags behind.

**Contract**: Constructor takes the three new repositories; `notes`, `topics`, `tags` attributes; `__aenter__` snapshots all five stores and `__aexit__` restores all five when `commit()` was not called.

#### 4. Composition roots

**File**: `backend/src/adapters/compose.py`, `backend/tests/integration/support/in_memory_capture.py`

**Intent**: One wiring change in production, the mirroring one in the test composition the integration and BDD suites share.

**Contract**: Module-level singletons for the three repositories and the embedding adapter; both `_unit_of_work()` and `InMemoryCaptureComposition` construct the five-repository UnitOfWork; `InMemoryCaptureComposition` exposes the new repositories and the embedding adapter as fields.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest` green
- `cd backend && uv run basedpyright` clean

---

## Phase 7: In-memory persistence and UnitOfWork — behavior

### Overview

Implements the adapters and proves them against one contract suite per port, plus a rollback test spanning the extended commit boundary.

### Changes Required:

#### 1. Adapter implementations

**File**: `backend/src/adapters/out/in_memory/capture/note_repository.py`, `topic_repository.py`, `tag_repository.py`, `embedding.py`, `unit_of_work.py`

**Intent**: Straightforward dict-backed storage with deep-copy snapshots, matching the existing adapters exactly.

**Contract**: `add` stores by `id.value`; `get` returns `None` on a miss; `snapshot`/`restore` deep-copy. `DeterministicEmbeddingAdapter.embed` derives its vector from a stable hash of the trimmed text.

#### 2. Contract suites

**File**: `backend/tests/unit/capture/contracts/test_note_repository_contract.py`, `test_topic_repository_contract.py`, `test_tag_repository_contract.py`, `test_embedding_contract.py`

**Intent**: One behavioral contract per port, parametrized over implementations, per the contract-testing rule — so the SQL adapters that come later inherit a runnable specification.

**Contract**: Each repository suite asserts round-trip through `add`/`get`, `None` on an unknown id, and that a second `add` of the same id overwrites. The embedding suite asserts determinism, a stable non-zero dimension, and that different texts yield different vectors.

#### 3. Rollback test

**File**: `backend/tests/unit/capture/test_unit_of_work.py`

**Intent**: The "rollback the whole turn" answer is only real if the new stores are inside the snapshot set.

**Contract**: Adding a note, a topic and a tag inside the context manager without calling `commit()` leaves all three absent afterwards; the same sequence with `commit()` leaves all three present.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/contracts -v` green
- `cd backend && uv run pytest tests/unit/capture/test_unit_of_work.py -v` green
- `cd backend && uv run pytest` green

---

## Phase 8: Vocabulary resolver and command routing — stubs

### Overview

Introduces the application service that turns proposed labels into persisted aggregates, and the routing skeleton inside the reply command.

### Changes Required:

#### 1. Vocabulary resolver

**File**: `backend/src/application/capture/services/__init__.py`, `backend/src/application/capture/services/vocabulary.py`

**Intent**: The ADR puts reconciliation in an application service so the aggregates never see candidate strings. In this slice the service always mints; S-05 rewrites its body to reuse-or-mint without touching any caller.

**Contract**: A concrete class, not a protocol — there is exactly one implementation and S-05 replaces it in place.

```python
class VocabularyResolver:
    def __init__(self, embedding: EmbeddingPort) -> None: ...

    async def resolve_topic(
        self, label: Label, topics: TopicRepository
    ) -> Topic: ...

    async def resolve_tag(self, label: Label, tags: TagRepository) -> Tag: ...
```

#### 2. Command dependencies and routing skeleton

**File**: `backend/src/application/capture/commands/send_message.py`, `backend/src/adapters/compose.py`, `backend/tests/integration/support/in_memory_capture.py`

**Intent**: Give the command what it needs to draft, and shape the per-kind dispatch the next phase fills in.

**Contract**: `GenerateReplyCommand.__init__` gains `vocabulary: VocabularyResolver`. `handle()` gains a per-chunk dispatch over the four kinds with the draft branches unimplemented. Both composition roots construct and inject the resolver.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest` green
- `cd backend && uv run basedpyright` clean

---

## Phase 9: Vocabulary resolver and command routing — behavior

### Overview

The drafting path end to end inside the application layer: resolve, stream, persist, commit, announce.

### Changes Required:

#### 1. Resolver implementation

**File**: `backend/src/application/capture/services/vocabulary.py`

**Intent**: Embed the label, mint the aggregate, persist it — the mint half of the reuse-or-mint mechanism.

**Contract**: `resolve_topic` calls `embedding.embed(label.value)`, `Topic.mint(label, embedding)`, `topics.add(topic)`, and returns the topic. `resolve_tag` is the same over `Tag`.

#### 2. Chunk routing and draft assembly

**File**: `backend/src/application/capture/commands/send_message.py`

**Intent**: Turn the marked stream into SSE events and one persisted draft, without changing the conversation path's behavior or its failure semantics.

**Contract**: Within the existing single `async with self._uow` block: `ReplyTextChunk` accumulates reply text and yields `ReplyDeltaEvent` as today. `DraftTopicChunk` resolves through the resolver, then yields `DraftTopicEvent(label=<resolved label>)`. `DraftTagChunk` resolves and yields `DraftTagEvent`, appending to an ordered tag list. `DraftContentChunk` accumulates and yields `DraftDeltaEvent`. After the stream: the agent `Message` is recorded from the accumulated reply text; when any draft chunk was seen, `session.draft_note(topic, NoteContent(value=<accumulated>), tags)` runs, `uow.notes.add(note)` and `uow.capture_sessions.save(session)` follow, `DraftDoneEvent` is constructed, then `uow.commit()`. `DraftDoneEvent` and `ReplyDoneEvent` are both yielded after the block exits, draft first.

#### 3. Unit tests

**File**: `backend/tests/unit/capture/test_send_message_command.py`

**Intent**: Pin the event sequence, the persistence effects, and both failure paths.

**Contract**: A drafting transcript produces `delta`* → `draft_topic` → `draft_tag`* → `draft_delta`* → `draft_done` → `done`; the persisted `Note` carries the resolved `topic_id` and `tag_ids` in order and status `draft`; `session.note_id` names it; an exception raised mid-stream leaves no note, topic, tag or message behind; a second confirmation in the same session surfaces `SessionNoteAlreadyDraftedError`; a non-drafting turn emits exactly what it emitted before this slice.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture -v` green
- `cd backend && uv run pytest` green

### Review r3

Artifact: `reviews/2026-09-01-r3-property-test-phase-9.md`

- `R3-F1` — DraftDoneEvent content must match persisted note content after NoteContent stripping
  Fix: the shrunk padded body (`' 0 '` / `'  padded body  '`) must make `draft_done.content == note.content.value` in the example suite until fixed, then remain as regression
- `R3-F2` — Draft stream without draft_topic must raise CoreException not AssertionError
  Fix: the orphan-tag stream must raise `CoreException` (not `AssertionError`) in the example suite until fixed, then remain as regression

---

## Phase 10: HTTP integration and acceptance scenarios (AC-08, AC-09)

### Overview

Proves the slice over the wire and writes the Gherkin scenarios for the two acceptance criteria this slice owns. The scenarios are themselves the tests, written here rather than generated by a separate pass.

### Changes Required:

#### 1. SSE integration test

**File**: `backend/tests/integration/test_capture_http.py`

**Intent**: The event sequence is what the TUI consumes; asserting it at the HTTP boundary catches serialization and discriminator mistakes the unit tests cannot.

**Contract**: A drafting turn over `POST /capture-sessions/{id}/messages` yields SSE frames whose `type` values follow `delta`* → `draft_topic` → `draft_tag`* → `draft_delta`* → `draft_done` → `done`, and the `draft_done` frame carries `note_id`, `topic`, `content` and `tags`.

#### 2. Acceptance scenarios

**File**: `backend/tests/features/capture-flow/US-04-draft-note.feature`, `backend/tests/bdd/steps/draft_note.py`, `backend/tests/bdd/test_features.py`, `backend/pyproject.toml`

**Intent**: AC-08 and AC-09 are the slice's contract with the effort; AC-09 needs a scenario showing the drafted topic differing from the session topic the user named.

**Contract**: Two `@capture-flow`-tagged scenarios, `@AC-08` and `@AC-09`, driven through `capture_client` against `InMemoryCaptureComposition`. AC-08 asserts the draft carries a topic, a non-empty body and at least one tag. AC-09 asserts the drafted topic label differs from the session topic extracted at session start. `bdd.steps.draft_note` is registered in `pytest_plugins`; `AC-05` through `AC-09` markers are added to `[tool.pytest.ini_options]`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/bdd -m "capture-flow and (AC-08 or AC-09)" -v` green
- `cd backend && uv run pytest tests/integration -v` green
- `cd backend && uv run pytest` green

#### Manual Verification:
- `cd backend && uv run fastapi dev src/main.py`, then `curl -N -X POST localhost:8000/capture-sessions` and `curl -N -X POST localhost:8000/capture-sessions/<id>/messages -H 'Content-Type: application/json' -d '{"content":"..."}'` twice — once conversational, once with a confirmation phrase — and read the SSE frames.

---

## Phase 11: TUI data layer — stubs

### Overview

Declares the client-side mirror of the four new events and the store slice that holds the incoming draft.

### Changes Required:

#### 1. Stream event types

**File**: `tui/src/api/stream.ts`

**Intent**: The hand-declared types in this module are the source of truth for SSE payloads, because the generator emits `unknown` for this route.

**Contract**: `DraftTopicEvent`, `DraftTagEvent`, `DraftDeltaEvent`, `DraftDoneEvent` (with `noteId`, `topic`, `content`, `tags`) added to the `ReplyStreamEvent` union, plus matching snake_case variants in `RawReplyStreamEvent`.

#### 2. Store slice

**File**: `tui/src/store/chat.ts`

**Intent**: One place holding the draft as it arrives, shaped so the screen can render partial state.

**Contract**: `type Draft = { topic: string | null; tags: string[]; content: string; noteId: string | null }`; `draft: Draft | null` on `ChatState`, initially `null`.

### Success Criteria:

#### Automated Verification:
- `pnpm --dir tui typecheck` clean
- `pnpm --dir tui test` green
- `pnpm --dir tui lint` clean

---

## Phase 12: TUI data layer — behavior

### Overview

Parses the new frames and reduces them into the draft slice.

### Changes Required:

#### 1. Parser branches

**File**: `tui/src/api/stream.ts`

**Intent**: Map each new frame to its camelCase client shape, alongside the existing three.

**Contract**: `parseStreamEvent` handles `draft_topic`, `draft_tag`, `draft_delta` and `draft_done`, mapping `message_id`/`note_id`/`coverage_confidence` to their camelCase forms.

#### 2. Store reducers

**File**: `tui/src/store/chat.ts`

**Intent**: Accumulate the draft as it streams, then adopt the authoritative payload — the joined fragments and the persisted value can differ, because `NoteContent` trims and validates and because S-05 will resolve a topic label the model did not propose.

**Contract**: `draft_topic` opens the draft slice and sets `topic`; `draft_tag` appends to `tags`; `draft_delta` appends to `content`; `draft_done` replaces `topic`, `content` and `tags` wholesale with the event's values and sets `noteId`. A new `sendUserMessage` call and a `streamError` both reset `draft` to `null`.

#### 3. Tests

**File**: `tui/test/stream.test.ts`, `tui/test/chat.test.ts`

**Contract**: Parser round-trips each of the four frames; the store accumulates a full drafting sequence, and `draft_done` overrides a locally accumulated body that differs from the server's.

### Success Criteria:

#### Automated Verification:
- `pnpm --dir tui test` green
- `pnpm --dir tui typecheck` clean

---

## Phase 13: TUI screen — stubs

### Overview

Places the draft panel in the layout without rendering anything yet.

### Changes Required:

#### 1. Draft panel placeholder

**File**: `tui/src/screens/CaptureScreen.tsx`

**Intent**: Fix the panel's position in the layout — below the transcript, above the coverage banner — so the next phase only fills it in.

**Contract**: `function DraftNotePanel({ draft }: { draft: Draft | null })` returning `null`, rendered between the transcript `Box` and `CoverageBanner`, reading `draft` from the store.

### Success Criteria:

#### Automated Verification:
- `pnpm --dir tui test` green
- `pnpm --dir tui typecheck` clean

---

## Phase 14: TUI screen — behavior

### Overview

Renders the draft as it streams and keeps the brand header's row budget honest.

### Changes Required:

#### 1. Draft panel

**File**: `tui/src/screens/CaptureScreen.tsx`

**Intent**: Show the draft as a distinct, persistent block rather than a transcript line, because S-06 attaches reshape and approve to exactly this surface.

**Contract**: When `draft` is non-null the panel renders a bold topic heading, the tag labels on one line, and the body text, each appearing as soon as its part of the stream arrives. Returns `null` when `draft` is `null`.

#### 2. Row budget

**File**: `tui/src/screens/CaptureScreen.tsx`

**Intent**: `shouldShowWelesBrand` subtracts a term per fixed block; a new block that is not counted makes the header overflow the terminal.

**Contract**: `shouldShowWelesBrand` takes a `hasDraft` argument and subtracts a `draftBlock` term, following the existing `bannerBlock` pattern.

#### 3. Tests

**File**: `tui/test/captureScreen.test.tsx`

**Contract**: The panel is absent with no draft; with a partial draft it shows the topic and the tags received so far; with a completed draft it shows the body. The brand header is hidden when the draft block consumes the remaining budget.

### Success Criteria:

#### Automated Verification:
- `pnpm --dir tui test` green
- `pnpm --dir tui typecheck` clean
- `pnpm --dir tui lint` clean

#### Manual Verification:
- `cd backend && uv run fastapi dev src/main.py` in one shell, `pnpm --dir tui build && node tui/dist/cli.js` in another; hold a short conversation, then type a confirmation phrase and watch the draft panel fill in topic, then tags, then body.

---

## Testing Strategy

### Unit Tests:
Domain value-object validation and the three factories; both `draft_note()` guards, including the closed-session guard against a directly constructed closed session since HTTP cannot reach it in this slice; `VocabularyResolver` minting; `GenerateReplyCommand` chunk routing, event ordering, persistence effects and rollback; the TUI parser and store reducers.

### Integration Tests:
One contract suite per new port (`NoteRepository`, `TopicRepository`, `TagRepository`, `EmbeddingPort`) parametrized over implementations, plus the extended `ReplyGenerationPort` suite covering chunk kinds and ordering. `InMemoryUnitOfWork` rollback across all five stores. The SSE event sequence over the HTTP boundary.

### Manual Testing Steps:
Run the backend and the TUI, hold a short conversation, then type a confirmation phrase; confirm the draft panel fills in topic, then tags, then body, and that a second confirmation surfaces the "session already has a draft" error rather than producing a second note.

## Performance Considerations

The topic and tag labels are resolved before their SSE events go out, so each costs one `embed()` round trip before the TUI's heading and tag list appear. With the deterministic adapter this is negligible; with a real embedding service it is the first place latency will show. It is accepted deliberately: emitting the model's proposal early would make the heading rewrite itself once S-05 introduces reuse.

The whole turn runs inside one `UnitOfWork`, so a long note body holds the transaction open for the duration of the stream. Acceptable for a single-user tool and consistent with how the conversation path already behaves.

## Migration Notes

Phase 1 renames two exception classes, which changes their wire-visible `code` values from `empty_topic`/`topic_too_long` to `empty_session_topic`/`session_topic_too_long`. Nothing consumes those codes — the TUI renders `detail` — and the exhaustiveness test catches any table entry missed.

`CaptureSession` gains `note_id`, defaulting to `None`. There is no persistent store yet, so no data migration exists to write.

## References

- `context/adrs/capture-flow-domain-shape/decision.md` — the decided aggregate shapes, the two-Topic distinction, and reconciliation living outside the domain
- `context/adrs/hexagonal-arch-shape/decision.md` — layering, CQRS-lite, InMemoryFirst, no bus
- `context/efforts/capture-flow/prd.md:48-49,62` — FR-007, FR-008, and the one-note-per-session non-goal
- `context/efforts/capture-flow/stories.md:46-47` — AC-08, AC-09
- `context/efforts/capture-flow/roadmap.md:56-62` — slice S-04
- `context/changes/capture-flow-draft-note/research.md` — the model requirements synthesis and its three open questions, all resolved in this plan
- `context/foundation/rules/` — layering, cqrs-lite, exceptions, contract-testing, code-ordering
- `context/foundation/test-stack.md` — runners and acceptance-suite commands
