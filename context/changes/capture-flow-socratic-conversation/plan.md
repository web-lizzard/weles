# Capture Flow — Socratic Conversation Implementation Plan

## Overview

Implements slice S-01 of the `capture-flow` effort: a user can start a capture session and have the agent probe their understanding through Socratic follow-up questions (AC-01–AC-04). This plan covers the full vertical slice — domain model, application layer, HTTP adapter, and the TUI chat screen — because the user explicitly brought the TUI into scope for this change, with streaming conversation delivery over SSE.

The Socratic "probing" mechanics (topic extraction, solid/shaky assessment, follow-up generation) are built as three real, swappable outbound ports from day one, but backed by deterministic stand-in adapters in this change. The real `pydantic-ai`-backed adapters are deferred to a later change — this plan's job is to get the ports, Value Objects, and streaming contract right enough that swapping in a real LLM adapter later touches only `adapters/out/llm/capture/`.

## Current State Analysis

- `backend/src/domain/capture/`, `backend/src/application/capture/`, and any capture-specific adapter live nowhere yet — this is greenfield within an existing hexagonal skeleton (`backend/src/{domain,application,adapters}/`, `domain/exceptions.py:CoreException`, `adapters/http/errors.py:core_exception_handler`).
- `tui/` is bootstrap-only: `tui/src/app.tsx` renders a static "Weles TUI — bootstrap OK" string, `tui/src/store/index.ts` is an empty Zustand store, `tui/src/api/client.ts` wraps `openapi-fetch` against a placeholder (empty) generated schema.
- Installed `fastapi==0.141.1` ships a native `fastapi.sse` module (`EventSourceResponse`) with first-class generator/streaming support wired into routing and OpenAPI generation — confirmed by reading `backend/.venv/lib/python3.12/site-packages/fastapi/{sse.py,routing.py}` directly. This supersedes the "declare `responses=` manually" workaround `tui-stack`'s ADR anticipated; no `sse-starlette` dependency is needed.
- `openapi-typescript@^7` (pinned in `tui/package.json`) is not confirmed to parse the OpenAPI 3.2 SSE `itemSchema` convention FastAPI emits for streaming routes — flagged as a real risk to verify during implementation, with a documented fallback.

### Key Discoveries

- `context/adrs/capture-flow-domain-shape/decision.md:21-32` — `CaptureSession`/`Message` aggregate shape and factories this plan realizes a subset of (only `start()`/`open`, and `record()`).
- `context/adrs/capture-flow-domain-shape/decision.md:62` — command handlers, not the aggregate, own status-guard enforcement; this plan's `load_open_session_for_turn` follows that pattern.
- `context/adrs/hexagonal-arch-shape/decision.md:16-35` — layering, CQRS-lite, InMemoryFirst, contract-testing, and exception-mapping rules this plan must satisfy for every new port.
- `context/adrs/tui-stack/decision.md:18-20` — streaming/async endpoints get a hand-written `fetch`/`ReadableStream` client layer, typed from backend-declared response models, not `openapi-fetch`.
- `backend/src/domain/exceptions.py:1-29` — existing `CoreException`/`code()` mechanism this plan's new exceptions plug into; verified (see below) that a `model_validator` raising a non-`ValueError` exception propagates unmodified through Pydantic v2, which is what lets a VO validator raise a `CoreException` subclass directly.
- `backend/src/adapters/http/errors.py:1-13` — existing `EXCEPTION_STATUS_MAP`, extended by this plan rather than replaced.
- `tui/package.json:21-37` — current TUI dependencies; this plan adds `ink-text-input` for the message box.
- Empirically verified (throwaway `httpx.ASGITransport` probe against the installed `fastapi==0.141.1`, not kept in the repo): an exception raised *inside* a `response_class=EventSourceResponse` generator route — before or after its first `yield` — is **not** caught by `add_exception_handler`; it surfaces as an unhandled `ExceptionGroup`, because FastAPI's SSE machinery constructs and commits the streaming response (a producer task inside an `anyio` task group) before the generator body has run at all. The same exception raised from a `Depends`-injected dependency **is** caught cleanly (confirmed: a clean 4xx via the registered handler). This is why turn validation is a dependency, not code inside the streaming command — see Critical Implementation Details.
- Also confirmed: Pydantic's own field constraints (`Field(min_length=..., max_length=...)`) are enforced by Pydantic's core validation *before* any `@model_validator` runs, and raise `pydantic.ValidationError` — not whatever a validator would have raised. Every domain/application VO in this plan must do its own non-empty/length checks by hand inside `model_validator(mode="after")` and must **not** declare `Field(min_length=/max_length=)` on the underlying string field, or its errors silently stop being `CoreException`s.

## Desired End State

A user runs the TUI, it opens a capture session against the running backend, the user types their first message, and the agent's Socratic reply streams back token-chunk-by-chunk in the terminal, with the session's topic (derived from that first message) displayed. Subsequent messages continue the same flow. Verified by: the BDD suite for AC-01–AC-04 passing, and a manual run of the built TUI CLI against a running backend.

## What We're NOT Doing

- No real LLM/`pydantic-ai` adapter — `TopicExtractionPort`, `ConfidenceAssessmentPort`, `ReplyGenerationPort` get deterministic stand-in adapters only.
- No `CaptureSession.draft_note`/`approve`/`close` — out of scope per S-04/S-06; `status` stays `open` for the whole slice (no transition to `closed` exists yet).
- No session persistence, listing, or resume (PRD Non-Goal) — the in-memory adapter is the only store, matching `InMemoryFirst`.
- No authentication — deferred with `repo-shape`'s auth mechanism, not decided here.
- No new observability/metrics infrastructure — standard Python `logging` only, no new dependency.
- No separate HTTP endpoint for reading the transcript — it's fetched internally by `GenerateReplyCommand` via `TranscriptQueryPort`, never exposed over HTTP in this slice (nothing needs to resume/list a session).
- No exposing `ConfidenceAssessment` to the TUI as a distinct UI element — deferred; for now it only shapes the generated reply text.
- Mutation/property testing is not part of this plan's phases — left to a separate `/mutation-test`/`/property-test` pass at the author's discretion.

## Implementation Approach

**Two HTTP endpoints, not three.** `POST /capture-sessions` (no body) creates and persists a real `CaptureSession` via `CaptureSession.start()` — no topic yet, since none exists before any message is sent. `POST /capture-sessions/{session_id}/messages` is the single combined "send message, get streamed reply" endpoint, used identically for the first and every later turn. On the first call for a session (`session.topic is None`), it derives the topic from that message via `TopicExtractionPort` and calls the new guarded `CaptureSession.assign_topic()` before proceeding — this is a deliberate, documented deviation from `capture-flow-domain-shape`'s literal `start(topic) -> CaptureSession` factory, forced by the no-body session-start endpoint (the id must exist before any topic-bearing content does).

**Turn validation is a read-only `Depends`; the write stays a single `UnitOfWork`.** `load_open_session_for_turn` — a plain, non-mutating function, wired as a FastAPI dependency of the `messages` route — builds `MessageContent` (can raise `EmptyMessageContentError`/`MessageContentTooLongError`) and loads the `CaptureSession` by id (can raise `CaptureSessionNotFoundError`/`CaptureSessionClosedError`), touching no repository write and no `UnitOfWork`. It hands the already-loaded `(session, content)` pair straight to `GenerateReplyCommand`, which does everything that mutates state — recording the user message, lazily assigning the topic, generating and streaming the reply, recording the agent message — inside **one** `async with uow: ... await uow.commit()`. This keeps the turn atomic (one commit, not two) while still routing every validation failure through FastAPI's normal exception handling, per the SSE-generator finding above.

**Why not stream session-creation too.** A header value computed inside an SSE generator's body cannot reliably reach the response — confirmed by reading `fastapi/routing.py`: for `is_sse_stream` routes, `response.headers.raw.extend(solved_result.response.headers.raw)` runs immediately after the generator object is *created*, before the generator body has executed even one line (Python generators don't run until first iterated). So a newly-minted `session_id` set as a header from inside the handler would never make it onto the response. Keeping session creation as a plain, non-streamed JSON call sidesteps this entirely.

**Streaming payload is a discriminated union**, not a single chunk type: `ReplyDeltaEvent{type:"delta", text}` for each generated fragment, and one terminal `ReplyDoneEvent{type:"done", message_id, content, topic}` carrying the server's canonical final text (not whatever the client concatenated) plus the session's current topic. Verified against `fastapi/routing.py:get_stream_item_type` that a `Union`/`Annotated[..., Field(discriminator=...)]` return-annotation on an async-generator route is accepted the same way a single model would be — no special-casing needed.

**Port contracts are VO-typed on the input side, primitive on the output side of `ReplyGenerationPort`.** `TopicExtractionPort.extract(MessageContent) -> Topic`, `ConfidenceAssessmentPort.assess(Transcript) -> ConfidenceAssessment`, and `ReplyGenerationPort.generate(Transcript, ConfidenceAssessment) -> AsyncIterator[str]` all take domain/application Value Objects rather than primitives, so these contracts survive the later swap to a real `pydantic-ai` adapter unchanged. `generate()`'s *output* is raw `str` chunks, not `MessageContent` — a streamed fragment (a partial word, a lone space) will not generally satisfy `MessageContent`'s own validation, so validation is deferred to the point the full reply is assembled.

**Queries share the write-side's in-memory store, not the domain repository.** `TranscriptQueryPort`'s in-memory adapter and `MessageRepository`'s in-memory adapter both wrap one `InMemoryMessageStore` instance, so a query immediately sees what a command just wrote, with no aggregate reconstruction — the concrete instance of `hexagonal-arch-shape`'s "same-store queries" consequence for this slice.

**TUI state is Zustand, deliberately wider than `tui-stack` scoped it.** That ADR reserves Zustand for background/cross-screen status, not domain-shaped chat state — this plan uses it for the chat transcript anyway, per explicit instruction during planning. Recorded here as a conscious, requested deviation, not an oversight.

## Critical Implementation Details

**Validation and guards for the streaming endpoint must run in a `Depends`, never inside the generator body.** Confirmed empirically against the installed `fastapi==0.141.1`: once a route is detected as an SSE generator (`response_class=EventSourceResponse`), FastAPI resolves its dependencies, then unconditionally constructs and returns a 200 `StreamingResponse` wrapping a producer task — all *before* the route function's own body has executed a single line. An exception raised anywhere inside that body (before or after any `yield`) propagates as an unhandled `ExceptionGroup` from the `anyio` task group during response teardown, bypassing `add_exception_handler` entirely; a real ASGI server would surface this as a broken/incomplete response, not a clean 4xx. An exception raised from a `Depends`-injected dependency, by contrast, is resolved *before* that commitment and is caught normally. Consequence: `load_open_session_for_turn` (content validation, session lookup/guard — no write) is wired as a dependency of the `messages` route; `GenerateReplyCommand`'s generator body only does work that cannot fail with this slice's deterministic adapters, and owns the turn's single `UnitOfWork` commit.

**VO validation must never rely on Pydantic's own field constraints.** `Field(min_length=..., max_length=...)` is enforced by Pydantic's core validation *before* any `@model_validator` runs, and raises `pydantic.ValidationError` on failure — not a `CoreException`, and not caught by the existing `core_exception_handler`/`EXCEPTION_STATUS_MAP` mechanism at all. Every string-backed VO (`Topic`, `MessageContent`, `ConfidencePoint`) declares its field as a bare `value: str` / `note: str` with **no** `Field(min_length=..., max_length=...)`, and does its own non-empty-after-strip and length-cap comparisons by hand inside `@model_validator(mode="after")`, raising the `CoreException` subclass directly. Verified locally that Pydantic v2 (`2.13.5`, installed) propagates a non-`ValueError`/`TypeError`/`AssertionError` exception raised inside a validator unmodified, rather than wrapping it into a `pydantic.ValidationError` — this is what lets a hand-written check raise `TopicTooLongError` (say) and have it actually surface as that type. Every VO unit test must assert the *exact* domain exception type (`pytest.raises(TopicTooLongError)`, not a bare `Exception` or `pydantic.ValidationError`), specifically to catch a future edit that reintroduces a `Field()` constraint by accident.

`InMemoryUnitOfWork` must give a real rollback, not just a no-op wrapper: it snapshots the `CaptureSessionRepository`'s and `MessageRepository`'s underlying dict/list state on `__aenter__`, and restores that snapshot on `__aexit__` if `commit()` was never called (including on the client disconnecting mid-stream, which propagates as a `CancelledError` through `GenerateReplyCommand`'s async generator). Without this, "commit after the stream drains" has nothing to actually roll back to.

`CaptureSession` and `Message` differ in mutability: `Message` has no mutators (per ADR) and can be a frozen `pydantic.BaseModel`; `CaptureSession` mutates (`assign_topic`, and later `close`) and must **not** be frozen. Only true Value Objects (`Topic`, `MessageContent`, `MessageRole`, `SessionId`, `MessageId`, `TranscriptEntry`, `ConfidencePoint`, `ConfidenceAssessment`) are frozen.

Length caps (`Topic` ≤ 200 chars, `MessageContent` ≤ 4000 chars) are this plan's own assumption — no upstream artifact specifies a number. Flagged here as easy to revise; not blocking.

## Phase 1: Domain model — stubs

### Overview

Materializes the domain-layer Contract symbols: Value Objects, the two aggregates, their ports, and their exceptions — no validation or business logic bodies yet.

### Changes Required:

#### 1. Value Objects

**File**: `backend/src/domain/capture/value_objects.py`

**Intent**: Give the domain a typed vocabulary for topic, message content, role, and both aggregate ids, instead of bare `str`/`UUID`.

**Contract**: `Topic(value: str)`, `MessageContent(value: str)`, `MessageRole(str, Enum)` (`USER`, `AGENT`), `SessionId(value: UUID)` with `SessionId.new()`, `MessageId(value: UUID)` with `MessageId.new()`, `SessionStatus(str, Enum)` (`OPEN`, `CLOSED`). All frozen `pydantic.BaseModel`s except the two enums. No validators yet (structure only).

#### 2. Aggregates

**File**: `backend/src/domain/capture/capture_session.py`

**Intent**: `CaptureSession` shape per `capture-flow-domain-shape`, restricted to what S-01 exercises.

**Contract**: `CaptureSession(id: SessionId, topic: Topic | None, status: SessionStatus, created_at: datetime)` — **not frozen**. `start() -> CaptureSession` (classmethod, mints its own id, `topic=None`, `status=OPEN`) and `assign_topic(self, topic: Topic) -> None` (instance method) declared with `raise NotImplementedError` bodies.

**File**: `backend/src/domain/capture/message.py`

**Intent**: `Message` shape per ADR — immutable, append-only.

**Contract**: `Message(id: MessageId, session_id: SessionId, role: MessageRole, content: MessageContent, created_at: datetime)` — frozen. `record(cls, session_id: SessionId, role: MessageRole, content: MessageContent) -> Message` classmethod, `raise NotImplementedError` body.

#### 3. Ports and exceptions

**File**: `backend/src/domain/capture/ports.py`

**Intent**: One repository-style port per aggregate root.

**Contract**: `CaptureSessionRepository(Protocol)` — `async def get(self, session_id: SessionId) -> CaptureSession | None`, `async def save(self, session: CaptureSession) -> None`. `MessageRepository(Protocol)` — `async def add(self, message: Message) -> None` only (the write path never needs to re-read message history).

**File**: `backend/src/domain/capture/exceptions.py`

**Intent**: Domain-raised errors for VO validation and aggregate guards, all rooted in the existing `CoreException`.

**Contract**: `EmptyTopicError`, `TopicTooLongError`, `EmptyMessageContentError`, `MessageContentTooLongError`, `CaptureSessionNotFoundError`, `CaptureSessionClosedError`, `SessionTopicAlreadyAssignedError` — each `class Foo(CoreException): pass`, importing `CoreException` from `domain.exceptions`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright src/domain/capture` — new modules type-check
- `cd backend && uv run pytest --collect-only tests/unit/capture` — nothing to collect yet is fine; import errors are not

---

## Phase 2: Domain model — behavior

### Overview

Real validation and factory/guard logic for everything Phase 1 stubbed.

### Changes Required:

#### 1. VO validation

**File**: `backend/src/domain/capture/value_objects.py`

**Intent**: Enforce "non-empty after strip" and a length cap on the two string-backed VOs.

**Contract**: `value: str` on both, with **no** `Field(min_length=/max_length=)` — length and emptiness are checked by hand. `Topic` and `MessageContent` each get a `@model_validator(mode="after")` that strips `.value`, raises `EmptyTopicError`/`EmptyMessageContentError` on empty, and raises `TopicTooLongError` (>200 chars) / `MessageContentTooLongError` (>4000 chars) otherwise — raised directly, not via `ValueError` and not via a Pydantic field constraint, per the Critical Implementation Details note above.

#### 2. Aggregate behavior

**File**: `backend/src/domain/capture/capture_session.py`

**Intent**: Real `start()`/`assign_topic()`.

**Contract**: `start()` returns `CaptureSession(id=SessionId.new(), topic=None, status=SessionStatus.OPEN, created_at=utcnow())`. `assign_topic(topic)` raises `SessionTopicAlreadyAssignedError` if `self.topic is not None`, else sets `self.topic = topic`.

**File**: `backend/src/domain/capture/message.py`

**Intent**: Real `record()`.

**Contract**: Returns `Message(id=MessageId.new(), session_id=session_id, role=role, content=content, created_at=utcnow())`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/test_value_objects.py tests/unit/capture/test_model.py -v` — each invalid-input case asserts the *exact* `CoreException` subclass (`pytest.raises(EmptyTopicError)`, `pytest.raises(TopicTooLongError)`, etc.), never a bare `Exception` or `pydantic.ValidationError`, to guard against a future edit reintroducing a `Field()` constraint
- `cd backend && uv run basedpyright src/domain/capture`

---

## Phase 3: Application ports & in-memory adapters — stubs

### Overview

Materializes every port the command layer will depend on (three agent ports, one query port, the `UnitOfWork`), plus the shape of every in-memory adapter, with no real behavior.

### Changes Required:

#### 1. Application-layer Value Objects and exceptions

**File**: `backend/src/application/capture/value_objects.py`

**Intent**: The internal (never-serialized) shapes the agent ports pass between each other.

**Contract**: `TranscriptEntry(role: MessageRole, content: MessageContent)` (frozen), `Transcript = list[TranscriptEntry]`, `ConfidencePointKind(str, Enum)` (`SOLID`, `SHAKY`), `ConfidencePoint(kind: ConfidencePointKind, note: str)` (frozen, no validator yet), `ConfidenceAssessment(points: list[ConfidencePoint])` (frozen).

**File**: `backend/src/application/capture/exceptions.py`

**Intent**: Application-layer counterpart to domain exceptions, same shared root.

**Contract**: `EmptyConfidencePointError(CoreException)`.

#### 2. Ports

**File**: `backend/src/application/capture/ports.py`

**Intent**: The three swappable agent ports and the transactional port.

**Contract**:
```python
class TopicExtractionPort(Protocol):
    async def extract(self, first_message: MessageContent) -> Topic: ...

class ConfidenceAssessmentPort(Protocol):
    async def assess(self, transcript: Transcript) -> ConfidenceAssessment: ...

class ReplyGenerationPort(Protocol):
    def generate(
        self, transcript: Transcript, assessment: ConfidenceAssessment
    ) -> AsyncIterator[str]: ...

class UnitOfWork(Protocol):
    capture_sessions: CaptureSessionRepository
    messages: MessageRepository
    async def __aenter__(self) -> "UnitOfWork": ...
    async def __aexit__(self, *exc: object) -> None: ...
    async def commit(self) -> None: ...
```

**File**: `backend/src/application/capture/queries/transcript.py`

**Intent**: Read-side port for assembling a session's transcript, independent of the domain repository.

**Contract**: `TranscriptQueryPort(Protocol)` — `async def get_transcript(self, session_id: SessionId) -> Transcript`.

#### 3. In-memory adapter shells

**File**: `backend/src/adapters/out/in_memory/capture/{message_store,capture_session_repository,message_repository,transcript_query,unit_of_work,topic_extraction,confidence_assessment,reply_generation}.py`

**Intent**: One file per adapter, matching one port each (plus the shared store), class/method signatures only.

**Contract**: `InMemoryMessageStore` (plain class, `add`/`list_by_session` methods), `InMemoryCaptureSessionRepository`, `InMemoryMessageRepository` (wraps `InMemoryMessageStore`), `InMemoryTranscriptQueryAdapter` (wraps the same store instance), `InMemoryUnitOfWork`, `DeterministicTopicExtractionAdapter`, `DeterministicConfidenceAssessmentAdapter`, `DeterministicReplyGenerationAdapter` — each implementing its port's method signatures with `raise NotImplementedError`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright src/application/capture src/adapters/out/in_memory/capture`

---

## Phase 4: Application ports & in-memory adapters — behavior

### Overview

Real logic for every adapter stubbed in Phase 3, plus one contract-test suite per port.

### Changes Required:

#### 1. `ConfidencePoint` validation

**File**: `backend/src/application/capture/value_objects.py`

**Intent**: Same non-empty-after-strip discipline as the domain string VOs.

**Contract**: `note: str` with **no** `Field(min_length=...)`. `ConfidencePoint` gets a `@model_validator(mode="after")` raising `EmptyConfidencePointError` directly when `note.strip()` is empty.

#### 2. Store, repositories, query

**File**: `backend/src/adapters/out/in_memory/capture/{message_store,capture_session_repository,message_repository,transcript_query}.py`

**Intent**: A single shared in-memory store backs both the write-side `MessageRepository` and the read-side `TranscriptQueryPort`, per the CQRS-lite "same store" pattern.

**Contract**: `InMemoryMessageStore.add(message)` appends to a `dict[UUID, list[Message]]` keyed by `session_id`; `list_by_session(session_id)` returns that list in insertion order. `InMemoryMessageRepository(store)` and `InMemoryTranscriptQueryAdapter(store)` both take the same `InMemoryMessageStore` instance by constructor injection. `InMemoryTranscriptQueryAdapter.get_transcript` maps each `Message` to `TranscriptEntry(role=message.role, content=message.content)`. `InMemoryCaptureSessionRepository` is a plain `dict[UUID, CaptureSession]` keyed by session id, `save` is an upsert.

#### 3. `InMemoryUnitOfWork`

**File**: `backend/src/adapters/out/in_memory/capture/unit_of_work.py`

**Intent**: Give the in-memory adapter genuine commit/rollback semantics, not just a pass-through, so the command layer's rollback-on-exception behavior is actually testable.

**Contract**: `__aenter__` snapshots (deep-copies) the underlying store/dict state of both injected repositories; `commit()` sets an internal flag; `__aexit__` restores the pre-`__aenter__` snapshot unless `commit()` was called, including when the generator using it is cancelled mid-stream.

#### 4. Deterministic stand-in adapters

**File**: `backend/src/adapters/out/in_memory/capture/{topic_extraction,confidence_assessment,reply_generation}.py`

**Intent**: Scripted, non-LLM implementations that still make AC-02–AC-04 observably true, so the vertical slice is genuinely exercised end to end.

**Contract**: `DeterministicTopicExtractionAdapter.extract(first_message)` derives a `Topic` from the first ~8 words of `first_message.value` (falling back to a fixed default string if that would be empty), always returning a valid `Topic`. `DeterministicConfidenceAssessmentAdapter.assess(transcript)` returns a `ConfidenceAssessment` with a templated solid point and shaky point derived from the latest user `TranscriptEntry` (empty `points` list only when the transcript has no user turns yet). `DeterministicReplyGenerationAdapter.generate(transcript, assessment)` yields a templated Socratic follow-up ("You've got a handle on: {solid}. Let's dig into: {shaky}. …") broken into small chunks with a short `asyncio.sleep` between them to simulate real streaming pacing.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/contracts -v` — one parametrized contract suite per port (`CaptureSessionRepository`, `MessageRepository`, `TranscriptQueryPort`, `TopicExtractionPort`, `ConfidenceAssessmentPort`, `ReplyGenerationPort`), asserting structural invariants (non-empty/valid output), not literal stand-in text
- `cd backend && uv run pytest tests/unit/capture -v` — `ConfidencePoint`'s empty-note case asserts `pytest.raises(EmptyConfidencePointError)` specifically, same exact-type discipline as Phase 2

---

## Phase 5: Application commands — stubs

### Overview

DTOs (fully defined — they're pure data) and command class shells.

### Changes Required:

#### 1. DTOs

**File**: `backend/src/application/capture/dto.py`

**Intent**: Wire-facing shapes, primitive-typed per `cqrs-lite.md` — never a domain VO leaking through.

**Contract**:
```python
class StartCaptureSessionResponseDTO(BaseModel):
    session_id: UUID

class SendMessageRequestDTO(BaseModel):
    content: str

class ReplyDeltaEvent(BaseModel):
    type: Literal["delta"] = "delta"
    text: str

class ReplyDoneEvent(BaseModel):
    type: Literal["done"] = "done"
    message_id: UUID
    content: str
    topic: str

ReplyStreamEvent = Annotated[ReplyDeltaEvent | ReplyDoneEvent, Field(discriminator="type")]
```

#### 2. Command shells

**File**: `backend/src/application/capture/commands/start_capture_session.py`

**Intent**: Thin command, one dependency.

**Contract**: `StartCaptureSessionCommand(uow: UnitOfWork)` with `async def handle(self) -> StartCaptureSessionResponseDTO`, body `raise NotImplementedError`.

**File**: `backend/src/application/capture/commands/send_message.py`

**Intent**: Split by what can fail and where FastAPI can still map that failure to a status code (see Critical Implementation Details) — a non-mutating validation step, and the mutating, streaming command.

**Contract**:
```python
async def load_open_session_for_turn(
    session_id: SessionId,
    raw_content: str,
    capture_sessions: CaptureSessionRepository,
) -> tuple[CaptureSession, MessageContent]: ...  # raise NotImplementedError

class GenerateReplyCommand:
    def __init__(
        self,
        uow: UnitOfWork,
        transcript_query: TranscriptQueryPort,
        topic_extraction: TopicExtractionPort,
        confidence_assessment: ConfidenceAssessmentPort,
        reply_generation: ReplyGenerationPort,
    ) -> None: ...

    async def handle(
        self, session: CaptureSession, content: MessageContent
    ) -> AsyncIterator[ReplyStreamEvent]: ...  # stub with `if False: yield` to keep the generator type
```
`load_open_session_for_turn` takes no `UnitOfWork` — it only reads, never writes, so it has nothing to commit or roll back.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright src/application/capture`

---

## Phase 6: Application commands — behavior

### Overview

Real orchestration logic for both commands.

### Changes Required:

#### 1. `StartCaptureSessionCommand`

**File**: `backend/src/application/capture/commands/start_capture_session.py`

**Intent**: Create and persist a bare, topic-less session.

**Contract**: `async with self._uow as uow: session = CaptureSession.start(); await uow.capture_sessions.save(session); await uow.commit()`, returns `StartCaptureSessionResponseDTO(session_id=session.id.value)`.

#### 2. `load_open_session_for_turn`

**File**: `backend/src/application/capture/commands/send_message.py`

**Intent**: Everything that can legitimately reject the request, with no persistence involved — safe to run as a FastAPI dependency, per the empirical SSE finding in Critical Implementation Details.

**Contract**: (1) `content = MessageContent(value=raw_content)` — raises `EmptyMessageContentError`/`MessageContentTooLongError`; (2) `session = await capture_sessions.get(session_id)` — raises `CaptureSessionNotFoundError` if `None`, raises `CaptureSessionClosedError` if `session.status != SessionStatus.OPEN`; (3) `return session, content`. No `UnitOfWork`, no write.

#### 3. `GenerateReplyCommand`

**File**: `backend/src/application/capture/commands/send_message.py`

**Intent**: Everything that mutates state for the turn, in one atomic commit: record the user message, lazily assign topic on turn one, generate and stream the reply, persist the agent message.

**Contract**: Takes the already-validated `(session, content)` from `load_open_session_for_turn` — no re-fetch, no re-validation. Order inside **one** `async with self._uow as uow: ...`: (1) `Message.record(session.id, MessageRole.USER, content)`, `uow.messages.add(...)`; (2) if `session.topic is None`: `topic = await self._topic_extraction.extract(content)`, `session.assign_topic(topic)`, `uow.capture_sessions.save(session)`; (3) `transcript = await self._transcript_query.get_transcript(session.id)`; (4) `assessment = await self._confidence_assessment.assess(transcript)`; (5) stream `self._reply_generation.generate(transcript, assessment)`, yielding `ReplyDeltaEvent(text=chunk)` per chunk while accumulating `full_text`; (6) after the generator drains: `reply_content = MessageContent(value=full_text)`, `agent_message = Message.record(session.id, MessageRole.AGENT, reply_content)`, `uow.messages.add(...)`, `await uow.commit()`; (7) `yield ReplyDoneEvent(message_id=agent_message.id.value, content=reply_content.value, topic=session.topic.value)` — outside the `async with` block, after commit.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/test_start_capture_session_command.py tests/unit/capture/test_send_message_command.py -v` — covers: `load_open_session_for_turn` raises `CaptureSessionNotFoundError` for an unknown id and `CaptureSessionClosedError` for a fixture-constructed closed session (status never transitions in this slice's production code, so this fixture bypasses the normal factory on purpose) with the *exact* exception type in both cases; `GenerateReplyCommand` — first-turn lazy topic assignment, second-turn skips it, commit happens only after the stream fully drains (one `uow.commit()` call, not two), an early `aclose()` on the generator leaves nothing persisted (rollback)

---

## Phase 7: HTTP adapter — stubs

### Overview

Route signatures and DI wiring skeleton, error-code table extended.

### Changes Required:

#### 1. Routes

**File**: `backend/src/adapters/http/capture.py`

**Intent**: Two routes matching the design above.

**Contract**: `POST /capture-sessions` (no request body) → `StartCaptureSessionResponseDTO`, via `Depends(StartCaptureSessionCommand)`. `POST /capture-sessions/{session_id}/messages`, body `SendMessageRequestDTO`, `response_class=EventSourceResponse`, return annotation `AsyncIterator[ReplyStreamEvent]` — its `(session, content)` parameter comes from `Depends(get_turn_context)`, a small wrapper `Depends` that calls `load_open_session_for_turn`; the route's own body is just `async for event in command.handle(session, content): yield event`, nothing else, so it stays exception-free by construction. Dependency-provider functions exist but return not-yet-wired instances.

#### 2. Error mapping

**File**: `backend/src/adapters/http/errors.py`

**Intent**: Extend the existing table, don't replace it.

**Contract**: Add to `EXCEPTION_STATUS_MAP`: `capture_session_not_found: 404`, `capture_session_closed: 409`, `session_topic_already_assigned: 409`, `empty_topic: 422`, `topic_too_long: 422`, `empty_message_content: 422`, `message_content_too_long: 422`, `empty_confidence_point: 422`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright src/adapters/http/capture.py`
- `cd backend && uv run pytest tests/unit/test_http_error_mapping.py -v` — extend the existing exhaustiveness test (`CoreException.__subclasses__()` walk) to cover the new codes

---

## Phase 8: HTTP adapter — behavior

### Overview

Real dependency wiring (the composition root for this slice), router registration, and integration tests.

### Changes Required:

#### 1. Composition root and wiring

**File**: `backend/src/adapters/http/capture.py`

**Intent**: One shared `InMemoryMessageStore` feeds both the message repository and the transcript query adapter; one shared `InMemoryUnitOfWork` wraps both repositories.

**Contract**: Module-level singletons (store, repos, three stand-in adapters, `UnitOfWork`) constructed once; `Depends`-based provider functions build `StartCaptureSessionCommand`, `get_turn_context` (wrapping `load_open_session_for_turn` with the singleton `CaptureSessionRepository`), and `GenerateReplyCommand` from them per request.

**File**: `backend/src/main.py`

**Intent**: Wire the new router in.

**Contract**: `app.include_router(capture_router)`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/integration/test_capture_http.py -v` — via `httpx.AsyncClient(transport=httpx.ASGITransport(app=app))` and `client.stream(...)`: session creation returns a valid UUID; first message triggers a `delta*` then one `done` event carrying a non-empty `topic`; a second message on the same session streams without re-deriving the topic; unknown session id → clean 404 (via `get_turn_context`'s `Depends`, not a broken stream); empty message body → clean 422 (same path) — this is the concrete regression test for the empirical FastAPI/SSE finding in Critical Implementation Details

#### Manual Verification:
- `cd backend && uv run fastapi dev src/main.py`, then in another terminal: `curl -s -X POST localhost:8000/capture-sessions` to get a `session_id`, then `curl -N -X POST localhost:8000/capture-sessions/<id>/messages -H 'Content-Type: application/json' -d '{"content": "I want to talk through how TCP handshakes work"}'` and eyeball the SSE stream

---

## Phase 9: Acceptance scenarios (BDD, AC-01–AC-04)

### Overview

Validates the completed vertical slice directly against the four acceptance criteria this change realizes. Not a stubs/behavior pair — there's no new production code here, only test artifacts over what Phases 1–8 already built.

### Changes Required:

#### 1. Feature file and steps

**File**: `backend/tests/features/capture-flow/US-01-socratic-conversation.feature`

**Intent**: One scenario per AC-01–AC-04, tagged for the existing marker convention.

**Contract**: Gherkin scenarios tagged `@capture-flow @AC-01` etc., driving the HTTP layer exactly as a real client would (start session, send message, assert streamed reply shape and content-bearing behavior for AC-02/AC-03/AC-04).

**File**: `backend/tests/bdd/steps/capture.py`

**Intent**: Step definitions, imported from the existing loader.

**Contract**: New module imported from `backend/tests/bdd/test_features.py` per the append-only convention in `test-stack.md`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/bdd -m "capture-flow and (AC-01 or AC-02 or AC-03 or AC-04)" -v`

---

## Phase 10: TUI data layer — stubs

### Overview

Types and function/store signatures for the streaming client and chat store — no implementation.

### Changes Required:

#### 1. Stream client types and signatures

**File**: `tui/src/api/stream.ts`

**Intent**: Mirror the backend's `ReplyStreamEvent` union on the TS side.

**Contract**: `type ReplyDeltaEvent = {type: "delta"; text: string}`, `type ReplyDoneEvent = {type: "done"; messageId: string; content: string; topic: string}`, `type ReplyStreamEvent = ReplyDeltaEvent | ReplyDoneEvent`. Function signatures `startCaptureSession(): Promise<{sessionId: string}>` and `sendMessage(sessionId: string, content: string): AsyncGenerator<ReplyStreamEvent>`, unimplemented.

#### 2. Store shape

**File**: `tui/src/store/chat.ts`

**Intent**: Replace the placeholder store with the real chat state shape.

**Contract**: `useChatStore` state: `sessionId: string | null`, `topic: string | null`, `transcript: {role: "user" | "agent"; content: string}[]`, `currentReply: string`, `isStreaming: boolean`; actions `initSession()`, `sendUserMessage(text: string)` declared, unimplemented.

#### 3. Codegen verification

**File**: (none — verification step)

**Intent**: Confirm whether `openapi-typescript` produces a usable type for the SSE route before committing to a hand-maintained fallback.

**Contract**: Run `pnpm --dir tui generate:api` against a running dev backend; inspect `tui/src/api/generated/schema.d.ts` for the streaming route. If it's unusable (no `itemSchema` support in the installed `openapi-typescript` version), keep the hand-declared types in `stream.ts` as the source of truth and note the gap in a code comment pointing at this plan.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm typecheck`

#### Manual Verification:
- Run `pnpm --dir tui generate:api` against `uv run fastapi dev src/main.py` and inspect the generated schema for the streaming route, per the Contract above

---

## Phase 11: TUI data layer — behavior

### Overview

Real SSE parsing and store logic.

### Changes Required:

#### 1. Stream parsing and API calls

**File**: `tui/src/api/stream.ts`

**Intent**: Consume the backend's SSE stream without a parsing library, per `tui-stack`'s "small hand-written layer" decision.

**Contract**: `sendMessage` does a raw `fetch(..., {method: "POST", body: JSON.stringify({content})})`, pipes `response.body` through `TextDecoderStream`, buffers and splits on blank lines, strips the `data:` prefix, `JSON.parse`s each payload as `ReplyStreamEvent`, and `yield`s it. `startCaptureSession` uses the existing `openapi-fetch` client (`src/api/client.ts`) since it's a plain JSON POST.

#### 2. Store logic

**File**: `tui/src/store/chat.ts`

**Intent**: Pure reducer-style transitions driven by the stream.

**Contract**: `sendUserMessage(text)` pushes a `{role: "user", content: text}` entry, then `for await (const event of sendMessage(sessionId, text))`: on `delta`, append `event.text` to `currentReply`; on `done`, push `{role: "agent", content: event.content}` to `transcript` (using the server's canonical `content`, not the locally-accumulated `currentReply`), clear `currentReply`, set `topic`.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm test` — SSE parser tested against a fake `ReadableStream` built from an array of string chunks; store reducer tested by calling actions directly and asserting state, with `sendMessage` mocked at the module level

---

## Phase 12: TUI chat screen — stubs

### Overview

Component shell and the new input-handling dependency, wired to nothing yet.

### Changes Required:

#### 1. Dependency

**File**: `tui/package.json`

**Intent**: Add free-text keystroke input without hand-rolling cursor/backspace handling.

**Contract**: Add `ink-text-input` to `dependencies`.

#### 2. Screen shell

**File**: `tui/src/screens/CaptureScreen.tsx`

**Intent**: Component exists with its final structure, renders nothing store-driven yet.

**Contract**: `export default function CaptureScreen()` returning a static placeholder `<Text>` tree matching the eventual layout (transcript area + input area).

**File**: `tui/src/app.tsx`

**Intent**: Root renders the real screen.

**Contract**: `export default function App() { return <CaptureScreen />; }`.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm typecheck`

---

## Phase 13: TUI chat screen — behavior

### Overview

Wire the screen to the store and stream client; this is the user-visible end state.

### Changes Required:

#### 1. Full screen wiring

**File**: `tui/src/screens/CaptureScreen.tsx`

**Intent**: On mount, start a session; render finalized transcript, the in-flight reply, and an input box; submitting sends the next message.

**Contract**: `useEffect` on mount calls `initSession()`. `<Static items={transcript}>` renders each finalized `{role, content}` line — items here must stay append-only/immutable, never reordered or mutated, per Ink's `Static` contract. A separate, always-rerendering `<Text>{currentReply}</Text>` renders the in-flight reply below it. `<TextInput>` (from `ink-text-input`) captures the next message, calling `sendUserMessage` and clearing on submit; disabled (or submission no-ops) while `isStreaming`.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm test` — `ink-testing-library`: typing and submitting renders the user's message immediately; simulated delta events render incrementally in `lastFrame()`; the final frame after a `done` event shows the server's `content` in the transcript and clears the in-flight line; the displayed topic updates after the first turn's `done` event

#### Manual Verification:
- `uv run fastapi dev src/main.py` (backend) and, in another terminal, `cd tui && pnpm build && node dist/cli.js`: type a message that starts a topic, confirm the streamed reply renders progressively, then send a follow-up and confirm the conversation continues

---

## Testing Strategy

### Unit Tests:
Domain VOs/aggregates (Phase 2), application VOs (Phase 4), both commands (Phase 6) — all via `pytest`, in-memory-only, no I/O. Every invalid-VO-input test asserts the exact `CoreException` subclass raised (never a bare `Exception` or `pydantic.ValidationError`) — see Critical Implementation Details.

### Integration Tests:
Full HTTP surface via `httpx.ASGITransport` (Phase 8); TUI store + SSE parser via Vitest with a fake stream (Phase 11); TUI screen via `ink-testing-library` (Phase 13).

### Acceptance Tests:
`pytest-bdd` scenarios for AC-01–AC-04 (Phase 9), run against the real (in-memory-backed) HTTP stack, not mocks.

### Manual Testing Steps:
`curl -N` against the streaming endpoint (Phase 8); a real run of the built TUI CLI against the running backend (Phase 13).

## Performance Considerations

None specific to this slice — in-memory storage, a single-user tool, deterministic (non-LLM) stand-in adapters. The real cost driver (an actual LLM call per turn) is out of scope until the `pydantic-ai` adapter lands.

## Migration Notes

None — greenfield within an already-scaffolded hexagonal skeleton; no existing data or schema to migrate.

## References

- `context/changes/capture-flow-socratic-conversation/research.md` — domain-model scope for S-01
- `context/adrs/capture-flow-domain-shape/decision.md`
- `context/adrs/hexagonal-arch-shape/decision.md`
- `context/adrs/tui-stack/decision.md`
- `context/adrs/repo-shape/decision.md`
- `context/adrs/backend-stack/decision.md`
- `context/foundation/rules/{layering,cqrs-lite,contract-testing,exceptions,code-ordering}.md`
- `context/foundation/test-stack.md`
- `context/efforts/capture-flow/{prd,stories,roadmap}.md`
