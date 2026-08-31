# Capture Flow Send-Message Refactor: `guard_session` + Self-Loading `handle` + In-Band Stream Errors — Implementation Plan

> Revision 1 (2026-08-31): Replaced the `load_turn`-returns-`CaptureSession` design with `guard_session` (Depends-side, validates and returns only `MessageContent`) plus a `handle(session_id, content)` that loads its own session at the top of its own transaction. This structurally eliminates the R4-F1 staleness class (no caller-supplied `CaptureSession` parameter exists for it to manifest through) instead of deliberately reopening it, and gives `handle` its own existence/open-status guard for the rare TOCTOU window between `guard_session` and `handle`. Phases 1-2 rewritten wholesale (both unstarted); Phases 3-5 (TUI, renumbered from 4-6) are unaffected — the wire contract they depend on doesn't change. Prior version: `plan-versions/v1-plan.md`.

## Overview

`POST /capture-sessions/{session_id}/messages` currently keeps its pre-stream session/content guard as a free function, `load_open_session_for_turn`, wired into a `Depends` wrapper (`get_turn_context`) that sits beside `GenerateReplyCommand` rather than on it. This plan moves that guard onto `GenerateReplyCommand` as `guard_session` — a pure validator, still invoked from `Depends` so unknown/closed sessions and invalid content keep producing clean HTTP 4xx JSON, but returning only the validated `MessageContent`. `GenerateReplyCommand.handle` stops accepting a caller-supplied `CaptureSession` and instead loads its own, fresh, at the top of its own transaction — which structurally eliminates the R4-F1 staleness bug class rather than patching around it, and gives `handle` a defense-in-depth guard for the rare window between `guard_session` succeeding and `handle` running. It also adds an in-band `error` arm to the SSE stream so a `CoreException` raised *after* the 200 is committed (whether from `handle`'s own guard or, once real I/O-bound adapters land, from generation/extraction/commit) reaches the client instead of becoming a truncated stream / `ExceptionGroup`, and threads that error surface through to the TUI as a status-bar notification.

## Current State Analysis

- `load_open_session_for_turn` (`backend/src/application/capture/commands/send_message.py:26-37`) builds `MessageContent` (empty/too-long → 422), `get`s the session (`None` → 404), and rejects non-`OPEN` (409). No UoW, no write.
- `get_turn_context` (`backend/src/adapters/http/capture.py:32-43`) is the HTTP-side `Depends` wrapper that calls it, injected as the `turn` parameter of `send_message` (`backend/src/adapters/http/capture.py:55-65`).
- `GenerateReplyCommand.handle` (`backend/src/application/capture/commands/send_message.py:55-95`) takes a caller-supplied `(session, content)` on faith, owns the single `UnitOfWork`, and inside it re-reads the session (`uow.capture_sessions.get`, lines 64-72) purely to guard against a stale in-memory `topic` — the R4-F1 fix (`context/archive/changes/2026-08-29-capture-flow-socratic-conversation/plan.md:432`, review at `context/archive/changes/2026-08-29-capture-flow-socratic-conversation/reviews/2026-08-31-r4-property-test-phase-6.md`). That property-test pin was only ever a "proposed pin" in the review artifact — it was never merged into the live suite (confirmed: no `R4_F1`/`stale` hits under `backend/tests/`).
- `InMemoryCaptureSessionRepository.get`/`save` (`backend/src/adapters/out/in_memory/capture/capture_session_repository.py`) store and return the same object reference, no copy — the shared singleton in `compose.py` (`_capture_session_repository`) means every `get()` in a request currently observes the identical, live object. This is exactly why R4-F1 was possible in the first place: `handle` receiving a caller-supplied `CaptureSession` (rather than loading its own) is a design that only happens to be safe under this specific adapter.
- `ReplyStreamEvent` is `ReplyDeltaEvent | ReplyDoneEvent` only (`backend/src/application/capture/dto.py:15-29`); no error arm exists. `core_exception_handler`/`EXCEPTION_STATUS_MAP` (`backend/src/adapters/http/errors.py`) map `CoreException.code()` → HTTP status, but only for exceptions raised *before* the 200 is committed — FastAPI builds the `StreamingResponse` right after `Depends` resolution, before the generator body runs at all (confirmed against installed FastAPI 0.141.1; `backend/.venv/lib/python3.12/site-packages/fastapi/routing.py:481-646,1071-1077`).
- TUI: `stream.ts` (`tui/src/api/stream.ts`) throws a bare `Error("sendMessage failed: ${status}")` on `!response.ok`, discarding the JSON `{code, detail}` body; its `ReplyStreamEvent` union has no `error` arm. `chat.ts` (`tui/src/store/chat.ts`) has no `catch` around its streaming loop — only a `finally` — so any thrown error becomes an unhandled rejection. `CaptureScreen.tsx` fire-and-forgets `sendUserMessage` with `void`.
- Integration tests locking the pre-stream split: `test_unknown_session_returns_clean_404_before_streaming`, `test_empty_message_content_returns_clean_422_before_streaming` (`backend/tests/integration/test_capture_http.py:84-107`).
- Web/API convention (Anthropic, OpenAI, Gemini, FastAPI maintainer discussions) is a split, not "everything in the stream": errors known before any byte stay HTTP 4xx/5xx JSON; errors after headers flush become an in-band event, then the generator closes cleanly — never re-raises. Full citations in `research.md`. This was weighed explicitly against collapsing everything into the stream (dropping `Depends` entirely) — rejected because it breaks the documented convention, discards standard HTTP status semantics for every future client of this API, and would require rewriting the two tests above; kept for the record in case the trade-off is revisited.

## Desired End State

- `GenerateReplyCommand.guard_session(session_id, raw_content)` is the sole pre-stream check, called from `Depends` via `get_turn_context`, returning only the validated `MessageContent`; the free function `load_open_session_for_turn` is gone.
- Unknown session and empty/too-long content still produce clean HTTP 404/422 JSON, not a broken or 200 stream. Closed session remains HTTP 409 on the same path.
- `GenerateReplyCommand.handle(session_id, content)` loads its own `CaptureSession` at the top of its own transaction and re-validates existence/open-status itself — the R4-F1 staleness scenario is no longer expressible (there is no parameter through which a stale `CaptureSession` could be supplied), and a session that vanishes or closes in the narrow window between `guard_session` and `handle` now raises there instead of silently misbehaving.
- A `CoreException` raised inside `handle` after the 200 is committed — whether from `handle`'s own guard or a future I/O-bound adapter — yields exactly one `{type: "error", code, detail}` event, then the generator closes cleanly — no `ExceptionGroup`, no truncated stream. A non-`CoreException` failure still propagates unchanged (today's behavior) — adapters are expected to raise `CoreException` subclasses for their own failure modes.
- The TUI parses both `error` sources — the in-band SSE event and a pre-stream 4xx body — into one `streamError` store field, and `CaptureScreen` renders it as a status-bar notification that clears on the next successful send.

### Key Discoveries:

- FastAPI caches a dependency's result per request, keyed on the dependency callable — so `get_turn_context` can itself `Depends(get_generate_reply_command)` and call `.guard_session(...)` on it, and the route's own `Depends(get_generate_reply_command)` for the `command` parameter resolves to the *same* instance without a second construction. This is what lets `guard_session`'s call site "stay in Depends" while living on the command object (`backend/src/adapters/http/capture.py:55-65` — see Phase 1 Contract).
- Because `handle` now loads its own session fresh, in its own transaction, right before using it, the R4-F1 scenario is eliminated by construction, not by trust in a shared in-memory reference — this holds independent of adapter, in-memory or real. A real adapter's future locking need only wrap `handle`'s own `get()` (e.g. `SELECT ... FOR UPDATE`); no further signature change will be needed then.
- `core_exception_handler` already emits `{"code": exc.code(), "detail": str(exc)}` JSON on 4xx — the TUI's pre-stream path can reuse that shape directly instead of inventing a new one.
- Since the route no longer receives a `CaptureSession` object at all (only `session_id`/`MessageContent`), `capture.py` no longer needs to import the `CaptureSession` domain type — a small, incidental hexagonal-boundary tightening.

## What We're NOT Doing

- Collapsing 404/422/409 into a 200 SSE error event for *every* failure (see the rejected trade-off noted in Current State Analysis) — the pre-stream `Depends` path stays HTTP 4xx for the common, known-before-any-byte cases.
- Changing the route from an async-generator endpoint to `return EventSourceResponse(...)` to drop `Depends` — that fights FastAPI's native SSE `itemSchema` detection.
- Wiring real SQL/LLM adapters, or adding real row-level locking inside `handle`'s transaction — this change only makes `handle` load its own session and makes `CoreException` reportable in-band; it does not make any adapter fail differently.
- Catching non-`CoreException` failures inside the generator — those still propagate as today's broken-stream/`ExceptionGroup` behavior, per your call: adapters are expected to raise `CoreException` subclasses.
- A toast/notification library or timer-based auto-dismiss in the TUI — the status bar clears when the next message is sent, no new dependency.

## Implementation Approach

Backend first (Phases 1-2), each phase leaving the test suite fully green — no phase deletes something another still imports. TUI phases (3-5) follow the same wire shape backend Phase 2 establishes, working outward from the parser to the store to the rendered component, matching the existing one-concern-per-file test layout (`stream.test.ts`, `chat.test.ts`, `captureScreen.test.tsx`).

## Critical Implementation Details

FastAPI commits the `200`/`text/event-stream` response headers immediately after `Depends` resolution and before the generator body executes even once — a `raise` on the line right before a route's first `yield` is already too late; it becomes an unhandled `ExceptionGroup` with a `200` already sent, not a 4xx. `guard_session`'s execution must happen inside a `Depends`-resolved callable (`get_turn_context`), never inside the route's own generator body, including "above" the first `yield`. This is why Phase 1 keeps `get_turn_context` as a dependency function rather than inlining the check into `send_message`.

## Phase 1: `GenerateReplyCommand.guard_session` + self-loading `handle`

### Overview

Replaces the free function with `guard_session` (a pure Depends-side validator returning only `MessageContent`) and changes `handle` to take `session_id` instead of a caller-supplied `CaptureSession`, loading its own copy at the top of its own transaction — eliminating the R4-F1 staleness class structurally.

### Changes Required:

#### 1. Command gains `guard_session`; `handle` self-loads

**File**: `backend/src/application/capture/commands/send_message.py`

**Intent**: `guard_session` becomes the sole pre-stream check — a validator, not intake, since its only durable output the rest of the turn needs is `content`. `handle` stops trusting a caller-supplied session and becomes self-sufficient, matching the shape a future locked, real-adapter read will need without a further signature change.

**Contract**: `GenerateReplyCommand.__init__` gains a `capture_sessions: CaptureSessionRepository` parameter (first, ahead of `uow`, since both `guard_session` and `handle` need it). New/changed methods:

```python
async def guard_session(
    self, session_id: SessionId, raw_content: str
) -> MessageContent:
    content = MessageContent(value=raw_content)
    session = await self._capture_sessions.get(session_id)
    if session is None:
        raise CaptureSessionNotFoundError
    if session.status != SessionStatus.OPEN:
        raise CaptureSessionClosedError
    return content


async def handle(
    self, session_id: SessionId, content: MessageContent
) -> AsyncIterator[ReplyStreamEvent]:
    async with self._uow as uow:
        session = await uow.capture_sessions.get(session_id)
        if session is None:
            raise CaptureSessionNotFoundError
        if session.status != SessionStatus.OPEN:
            raise CaptureSessionClosedError

        user_message = Message.record(session.id, MessageRole.USER, content)
        await uow.messages.add(user_message)

        if session.topic is None:
            topic = await self._topic_extraction.extract(content)
            session.assign_topic(topic)
            await uow.capture_sessions.save(session)
        else:
            topic = session.topic
        # ... unchanged from here: transcript query, assessment, generate/stream,
        # commit, terminal ReplyDoneEvent yielded after the `async with` exits.
```

Same exception types as today (`CaptureSessionNotFoundError`, `CaptureSessionClosedError`, and `MessageContent`'s own `EmptyMessageContentError`/`MessageContentTooLongError`). The free function `load_open_session_for_turn` is removed entirely — no forwarding shim. `handle`'s old `persisted = await uow.capture_sessions.get(session.id)` staleness re-check (R4-F1) is gone too — not because it's deliberately accepted risk, but because `session` is now always the fresh read this same call just made, so `session.topic` can never disagree with what's persisted.

#### 2. Compose wiring

**File**: `backend/src/adapters/compose.py`

**Intent**: `get_generate_reply_command` supplies the new constructor dependency from the same shared singleton `get_turn_context` used to use directly.

**Contract**: `GenerateReplyCommand(capture_sessions=_capture_session_repository, uow=_unit_of_work(), transcript_query=_transcript_query, topic_extraction=_topic_extraction, confidence_assessment=_confidence_assessment, reply_generation=_reply_generation)`.

#### 3. HTTP `Depends` wrapper + route

**File**: `backend/src/adapters/http/capture.py`

**Intent**: `get_turn_context` calls `guard_session` on the same cached command instance the route injects as `command` — FastAPI dependency caching (per-request, keyed on the callable) guarantees they're identical, so no second `GenerateReplyCommand`/`UnitOfWork` gets built. The route no longer handles a `CaptureSession` object at all.

**Contract**:

```python
async def get_turn_context(
    session_id: UUID,
    body: SendMessageRequestDTO,
    command: Annotated[GenerateReplyCommand, Depends(get_generate_reply_command)],
) -> MessageContent:
    return await command.guard_session(SessionId(value=session_id), body.content)


@router.post(
    "/capture-sessions/{session_id}/messages",
    response_class=EventSourceResponse,
)
async def send_message(
    session_id: UUID,
    content: Annotated[MessageContent, Depends(get_turn_context)],
    command: Annotated[GenerateReplyCommand, Depends(get_generate_reply_command)],
) -> AsyncIterator[ReplyStreamEvent]:
    async for event in command.handle(SessionId(value=session_id), content):
        yield event
```

Drop the `get_capture_session_repository` import/`Depends` param, the `load_open_session_for_turn` import, and the now-unused `CaptureSession` import. Error handling around the `async for` lands in Phase 2.

#### 4. Test/composition call sites

**File**: `backend/tests/unit/capture/test_send_message_command.py`

**Intent**: Exercise `guard_session` and the self-loading `handle`; add coverage for `handle`'s own guard (the new TOCTOU-window behavior) alongside the existing topic-assignment tests, adjusted to the new `handle(session_id, content)` signature.

**Contract**: `_make_command_stack()` passes `capture_sessions=session_repo` into `GenerateReplyCommand(...)`. The three `test_load_open_session_for_turn_*` tests are renamed `test_guard_session_*` and call `stack.command.guard_session(...)`. The four `test_generate_reply_*` tests change their `stack.command.handle(session, content)` call to `stack.command.handle(session.id, content)` (each already `save()`s `session` into the repo first, so behavior is unchanged). Two new tests cover `handle`'s own guard:

```python
async def test_generate_reply_raises_not_found_if_session_missing_at_handle_time() -> None:
    stack = _make_command_stack()
    content = MessageContent(value="Hello")

    with pytest.raises(CaptureSessionNotFoundError):
        async for _ in stack.command.handle(SessionId.new(), content):
            pass


async def test_generate_reply_raises_closed_if_session_closed_at_handle_time() -> None:
    stack = _make_command_stack()
    closed = CaptureSession(
        id=SessionId.new(), topic=None, status=SessionStatus.CLOSED,
        created_at=datetime.now(UTC),
    )
    await stack.session_repo.save(closed)
    content = MessageContent(value="Hello")

    with pytest.raises(CaptureSessionClosedError):
        async for _ in stack.command.handle(closed.id, content):
            pass
```

**File**: `backend/tests/integration/support/in_memory_capture.py`

**Intent**: The integration composition's override factory must satisfy the new constructor signature.

**Contract**: `override_generate_reply_command` passes `capture_sessions=composition.capture_sessions` into `GenerateReplyCommand(...)`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/test_send_message_command.py tests/integration/test_capture_http.py -v`

#### Manual Verification:
- `cd backend && uv run fastapi dev src/main.py`, then in another terminal: `curl -s -X POST localhost:8000/capture-sessions/00000000-0000-4000-8000-000000000001/messages -H 'Content-Type: application/json' -d '{"content": "hi"}'` and confirm a clean `404` JSON body with `"code": "capture_session_not_found"` — proving the new `Depends`-cached wiring still produces a pre-stream 4xx.

---

## Phase 2: In-band `CoreException` → `ReplyErrorEvent`

### Overview

Widens the SSE wire contract with an `error` arm and wraps the generator's post-`Depends` work so a `CoreException` raised inside `handle` — including `handle`'s own new guard from Phase 1 — becomes one clean in-band event instead of a broken stream.

### Changes Required:

#### 1. Wire contract

**File**: `backend/src/application/capture/dto.py`

**Intent**: A third, explicit arm for failures that occur after the 200 is already committed.

**Contract**:

```python
class ReplyErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    code: str
    detail: str


ReplyStreamEvent = Annotated[
    ReplyDeltaEvent | ReplyDoneEvent | ReplyErrorEvent, Field(discriminator="type")
]
```

`code`/`detail` mirror `core_exception_handler`'s JSON shape (`backend/src/adapters/http/errors.py:22`) — no new mapping table, no change to `EXCEPTION_STATUS_MAP`.

#### 2. Generator error handling

**File**: `backend/src/adapters/http/capture.py`

**Intent**: The route stays the only place that turns a domain/application failure into wire shape — narrowed to `CoreException`, per your call that adapters are expected to raise `CoreException` subclasses; anything else still propagates as today's broken-stream behavior.

**Contract**:

```python
async def send_message(...) -> AsyncIterator[ReplyStreamEvent]:
    try:
        async for event in command.handle(SessionId(value=session_id), content):
            yield event
    except CoreException as exc:
        yield ReplyErrorEvent(code=exc.code(), detail=str(exc))
        return
```

Add `from domain.exceptions import CoreException` and `ReplyErrorEvent` to this file's imports.

#### 3. Regression coverage for the mechanism

**File**: `backend/tests/integration/test_capture_http.py`

**Intent**: Prove a `CoreException` raised mid-`generate()` (i.e. after the 200 has gone out) becomes one `{type: "error", code, detail}` event and a clean stream close — using an existing, already-mapped exception class so the `CoreException` exhaustiveness test (`backend/tests/unit/test_http_error_mapping.py`) needs no change. `handle`'s own new guard (Phase 1) is already covered at the unit level, so this integration test focuses on the generation-time path.

**Contract**: A small local `ReplyGenerationPort` test double that yields one chunk then raises (e.g. `CaptureSessionClosedError`), threaded into a `capture_client`-equivalent `TestClient` via `InMemoryCaptureComposition` with `reply_generation` swapped before `dependency_overrides()` is called. Asserts: response status is still `200`; the SSE event list contains exactly one `delta`, then one `error` event carrying the exception's `code()`; no `done` event follows. The two existing pre-stream tests (`test_unknown_session_returns_clean_404_before_streaming`, `test_empty_message_content_returns_clean_422_before_streaming`) must stay green unmodified — they're the proof the split still holds.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/integration/test_capture_http.py tests/unit/capture/test_send_message_command.py tests/unit/test_http_error_mapping.py -v`

---

## Phase 3: TUI `stream.ts` — parse `error` events + richer pre-stream errors

### Overview

Teaches the hand-written SSE parser the new `error` arm, and stops discarding the JSON body FastAPI already sends on a pre-stream 4xx.

### Changes Required:

#### 1. Wire types + parser

**File**: `tui/src/api/stream.ts`

**Intent**: Mirror the backend's third arm; `code`/`detail` need no field-renaming (unlike `done`'s `message_id` → `messageId`).

**Contract**: `ReplyErrorEvent = { type: "error"; code: string; detail: string }`; widen `ReplyStreamEvent` and `RawReplyStreamEvent`; `parseStreamEvent` passes the `error` variant through unchanged.

#### 2. Typed pre-stream error

**File**: `tui/src/api/stream.ts`

**Intent**: Give `chat.ts` something richer than a status code to show the user, reusing the `{code, detail}` shape `core_exception_handler` already sends.

**Contract**:

```typescript
export class SendMessageHttpError extends Error {
  constructor(public code: string, public detail: string, public status: number) {
    super(detail);
  }
}
```

`!response.ok` branch: attempt `await response.json()` and read `code`/`detail`; on success `throw new SendMessageHttpError(code, detail, response.status)`. On a parse failure or missing fields, fall back to today's `throw new Error("sendMessage failed: ${status}")`.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm exec vitest run test/stream.test.ts`

---

## Phase 4: TUI `chat.ts` store — `streamError` state

### Overview

Catches both error sources — the in-band event and the typed pre-stream throw — into one store field, clearing it at the start of the next send.

### Changes Required:

#### 1. Store state + handling

**File**: `tui/src/store/chat.ts`

**Intent**: One place the screen can read from regardless of which side of the 200 boundary the failure came from.

**Contract**: `ChatState` gains `streamError: { code: string; detail: string } | null`. `sendUserMessage` clears it in the same `set` call that appends the user transcript entry. The `for await` loop gains an `error` branch: `set({ streamError: { code: event.code, detail: event.detail } })`, then stop consuming (the server already ends the stream after an `error` event). The surrounding `try` gains a `catch (error)`: `SendMessageHttpError` instances map `{code: error.code, detail: error.detail}`; anything else maps to a generic fallback (e.g. `{code: "unknown_error", detail: error.message}}`) so `sendUserMessage`'s promise never rejects uncaught.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm exec vitest run test/chat.test.ts`

---

## Phase 5: TUI `CaptureScreen.tsx` — status-bar rendering

### Overview

Renders `streamError` as a status-bar row, following the existing `TopicHeading` pattern.

### Changes Required:

#### 1. Status bar component

**File**: `tui/src/screens/CaptureScreen.tsx`

**Intent**: Visible, distinguishable-from-transcript notification; no new UI library, no timer.

**Contract**: New `StatusBar({ error })` component (same file, alongside `TopicHeading`/`WelesBrand`), rendered when `streamError !== null`, showing `detail` in a distinct color. `shouldShowWelesBrand`'s row-budget math gains an `errorBlock` term mirroring `topicBlock`, so the banner doesn't silently overflow the terminal.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm exec vitest run test/captureScreen.test.tsx`

#### Manual Verification:
- `cd backend && uv run fastapi dev src/main.py` and, in another terminal, `cd tui && pnpm build && node dist/cli.js`: send a normal message end-to-end and confirm the status bar is absent and layout is unchanged — today's adapters never fail, so the error path itself isn't reachable through the live app yet, only through the automated tests above.

---

## Testing Strategy

### Unit Tests:
- Backend: `test_send_message_command.py` covers `guard_session`'s three exception paths, the four existing `handle` behavior tests adjusted to `handle(session_id, content)`, and two new tests for `handle`'s own guard (Phase 1).
- TUI: `stream.test.ts` covers the `error` parse arm and both `SendMessageHttpError` paths (Phase 3); `chat.test.ts` covers `streamError` set/clear from both sources (Phase 4).

### Integration Tests:
- `test_capture_http.py`: existing pre-stream 404/422 tests stay green unmodified; new mid-stream `CoreException` → in-band `error` test (Phase 2).

### Manual Testing Steps:
- Phase 1's curl repro (pre-stream 404 through the new wiring); Phase 5's end-to-end normal-path run (no regression in the built TUI).

## Performance Considerations

None — no new I/O, no new allocation on the hot path beyond one additional `try/except` frame in the generator and one additional store field in the TUI.

## Migration Notes

None — `ReplyStreamEvent`'s new `error` arm is additive; existing `delta`/`done` consumers are unaffected. No data migration.

## References

- `context/changes/capture-flow-socratic-conversation-send-mesage-refactor/frame.md`
- `context/changes/capture-flow-socratic-conversation-send-mesage-refactor/research.md`
- `context/archive/changes/2026-08-29-capture-flow-socratic-conversation/plan.md:432` (R4-F1 origin)
- `context/archive/changes/2026-08-29-capture-flow-socratic-conversation/reviews/2026-08-31-r4-property-test-phase-6.md` (R4-F1 proposed pin, never merged)
- `context/adrs/hexagonal-arch-shape/decision.md` (input-adapter-owns-mapping rule)
