# Capture Flow Send-Message Refactor: `load_turn` Ownership + In-Band Stream Errors — Implementation Plan

## Overview

`POST /capture-sessions/{session_id}/messages` currently keeps its pre-stream session/content guard as a free function, `load_open_session_for_turn`, wired into a `Depends` wrapper (`get_turn_context`) that sits beside `GenerateReplyCommand` rather than on it. This plan moves ownership of that pre-stream load onto `GenerateReplyCommand` itself as `load_turn`, still invoked from `Depends` (so unknown/closed sessions and invalid content keep producing clean HTTP 4xx JSON), and adds an in-band `error` arm to the SSE stream so a `CoreException` raised *after* the 200 is committed (once real I/O-bound adapters land) reaches the client instead of becoming a truncated stream / `ExceptionGroup`. It also removes a now-redundant defensive re-read in `GenerateReplyCommand.handle` (the R4-F1 guard) and threads the new error surface through to the TUI as a status-bar notification.

## Current State Analysis

- `load_open_session_for_turn` (`backend/src/application/capture/commands/send_message.py:26-37`) builds `MessageContent` (empty/too-long → 422), `get`s the session (`None` → 404), and rejects non-`OPEN` (409). No UoW, no write.
- `get_turn_context` (`backend/src/adapters/http/capture.py:32-43`) is the HTTP-side `Depends` wrapper that calls it, injected as the `turn` parameter of `send_message` (`backend/src/adapters/http/capture.py:55-65`).
- `GenerateReplyCommand.handle` (`backend/src/application/capture/commands/send_message.py:55-95`) assumes `(session, content)` is already valid, owns the single `UnitOfWork`, and inside it re-reads the session (`uow.capture_sessions.get`, lines 64-72) purely to guard against a stale in-memory `topic` — the R4-F1 fix (`context/archive/changes/2026-08-29-capture-flow-socratic-conversation/plan.md:432`, review at `context/archive/changes/2026-08-29-capture-flow-socratic-conversation/reviews/2026-08-31-r4-property-test-phase-6.md`). That property-test pin was only ever a "proposed pin" in the review artifact — it was never merged into the live suite (confirmed: no `R4_F1`/`stale` hits under `backend/tests/`).
- `InMemoryCaptureSessionRepository.get`/`save` (`backend/src/adapters/out/in_memory/capture/capture_session_repository.py`) store and return the same object reference, no copy — the shared singleton in `compose.py` (`_capture_session_repository`) means `load_turn`'s read and `handle`'s in-UoW read currently observe the identical object.
- `ReplyStreamEvent` is `ReplyDeltaEvent | ReplyDoneEvent` only (`backend/src/application/capture/dto.py:15-29`); no error arm exists. `core_exception_handler`/`EXCEPTION_STATUS_MAP` (`backend/src/adapters/http/errors.py`) map `CoreException.code()` → HTTP status, but only for exceptions raised *before* the 200 is committed — FastAPI builds the `StreamingResponse` right after `Depends` resolution, before the generator body runs at all (confirmed against installed FastAPI 0.141.1; `backend/.venv/lib/python3.12/site-packages/fastapi/routing.py:481-646,1071-1077`).
- TUI: `stream.ts` (`tui/src/api/stream.ts`) throws a bare `Error("sendMessage failed: ${status}")` on `!response.ok`, discarding the JSON `{code, detail}` body; its `ReplyStreamEvent` union has no `error` arm. `chat.ts` (`tui/src/store/chat.ts`) has no `catch` around its streaming loop — only a `finally` — so any thrown error becomes an unhandled rejection. `CaptureScreen.tsx` fire-and-forgets `sendUserMessage` with `void`.
- Integration tests locking the pre-stream split: `test_unknown_session_returns_clean_404_before_streaming`, `test_empty_message_content_returns_clean_422_before_streaming` (`backend/tests/integration/test_capture_http.py:84-107`).
- Web/API convention (Anthropic, OpenAI, Gemini, FastAPI maintainer discussions) is a split, not "everything in the stream": errors known before any byte stay HTTP 4xx/5xx JSON; errors after headers flush become an in-band event, then the generator closes cleanly — never re-raises. Full citations in `research.md`.

## Desired End State

- `GenerateReplyCommand.load_turn(session_id, raw_content)` is the sole pre-stream loader, called from `Depends` via `get_turn_context`; the free function `load_open_session_for_turn` is gone.
- Unknown session and empty/too-long content still produce clean HTTP 404/422 JSON, not a broken or 200 stream. Closed session remains HTTP 409 on the same path.
- The in-UoW staleness re-read in `handle` (R4-F1) is gone; a new test pins the resulting behavior explicitly (fresh extraction always wins over a stale caller-supplied `session.topic is None`), with a comment pointing at why this is an accepted, deliberate change.
- A `CoreException` raised inside `handle` after the 200 is committed yields exactly one `{type: "error", code, detail}` event, then the generator closes cleanly — no `ExceptionGroup`, no truncated stream. A non-`CoreException` failure still propagates unchanged (today's behavior) — adapters are expected to raise `CoreException` subclasses for their own failure modes.
- The TUI parses both `error` sources — the in-band SSE event and a pre-stream 4xx body — into one `streamError` store field, and `CaptureScreen` renders it as a status-bar notification that clears on the next successful send.

### Key Discoveries:

- FastAPI caches a dependency's result per request, keyed on the dependency callable — so `get_turn_context` can itself `Depends(get_generate_reply_command)` and call `.load_turn(...)` on it, and the route's own `Depends(get_generate_reply_command)` for the `command` parameter resolves to the *same* instance, with the same `UnitOfWork`, without a second `GenerateReplyCommand` construction. This is what lets `load_turn`'s call site "stay in Depends" while living on the command object (`backend/src/adapters/http/capture.py:55-65` — see Phase 1 Contract).
- Only the in-memory adapter makes "the caller's `session` is never actually stale" true; a real SQL adapter would restore the R4-F1 race. Removing the guard now is a deliberate, scoped trade — real adapters (out of scope here) are expected to close the gap with row-level locking at the transaction boundary, not with a second free-standing read.
- `core_exception_handler` already emits `{"code": exc.code(), "detail": str(exc)}` JSON on 4xx — the TUI's pre-stream path can reuse that shape directly instead of inventing a new one.

## What We're NOT Doing

- Collapsing 404/422/409 into a 200 SSE error event — the pre-stream `Depends` path stays HTTP 4xx.
- Changing the route from an async-generator endpoint to `return EventSourceResponse(...)` to drop `Depends` — that fights FastAPI's native SSE `itemSchema` detection.
- Wiring real SQL/LLM adapters, or adding the locking that will eventually replace the R4-F1 guard for a real database — this change only makes `CoreException` reportable in-band; it does not make any adapter fail differently.
- Catching non-`CoreException` failures inside the generator — those still propagate as today's broken-stream/`ExceptionGroup` behavior, per your call: adapters are expected to raise `CoreException` subclasses.
- A toast/notification library or timer-based auto-dismiss in the TUI — the status bar clears when the next message is sent, no new dependency.

## Implementation Approach

Backend first (Phases 1-3), each phase leaving the test suite fully green — no phase deletes something another still imports. TUI phases (4-6) follow the same wire shape backend Phase 3 establishes, working outward from the parser to the store to the rendered component, matching the existing one-concern-per-file test layout (`stream.test.ts`, `chat.test.ts`, `captureScreen.test.tsx`).

## Critical Implementation Details

FastAPI commits the `200`/`text/event-stream` response headers immediately after `Depends` resolution and before the generator body executes even once — a `raise` on the line right before a route's first `yield` is already too late; it becomes an unhandled `ExceptionGroup` with a `200` already sent, not a 4xx. `load_turn`'s execution must happen inside a `Depends`-resolved callable (`get_turn_context`), never inside the route's own generator body, including "above" the first `yield`. This is why Phase 1 keeps `get_turn_context` as a dependency function rather than inlining the load into `send_message`.

## Phase 1: `GenerateReplyCommand.load_turn` — move ownership + Depends wiring

### Overview

Moves `load_open_session_for_turn` onto `GenerateReplyCommand` as `load_turn`, gives the command a `capture_sessions` dependency, and rewires the HTTP `Depends` wrapper to resolve the same cached command instance the route already uses for `handle`.

### Changes Required:

#### 1. Command gains `load_turn`

**File**: `backend/src/application/capture/commands/send_message.py`

**Intent**: `load_turn` becomes the single owner of the pre-stream session/content guard; the free function is deleted.

**Contract**: `GenerateReplyCommand.__init__` gains a `capture_sessions: CaptureSessionRepository` parameter (first, ahead of `uow`, since it's what `load_turn` needs). New method:

```python
async def load_turn(
    self, session_id: SessionId, raw_content: str
) -> tuple[CaptureSession, MessageContent]:
    content = MessageContent(value=raw_content)
    session = await self._capture_sessions.get(session_id)
    if session is None:
        raise CaptureSessionNotFoundError
    if session.status != SessionStatus.OPEN:
        raise CaptureSessionClosedError
    return session, content
```

Same exception types as today (`CaptureSessionNotFoundError`, `CaptureSessionClosedError`, and `MessageContent`'s own `EmptyMessageContentError`/`MessageContentTooLongError`). The free function `load_open_session_for_turn` is removed entirely — no forwarding shim.

#### 2. Compose wiring

**File**: `backend/src/adapters/compose.py`

**Intent**: `get_generate_reply_command` supplies the new constructor dependency from the same shared singleton `get_turn_context` used to use directly.

**Contract**: `GenerateReplyCommand(capture_sessions=_capture_session_repository, uow=_unit_of_work(), transcript_query=_transcript_query, topic_extraction=_topic_extraction, confidence_assessment=_confidence_assessment, reply_generation=_reply_generation)`.

#### 3. HTTP `Depends` wrapper

**File**: `backend/src/adapters/http/capture.py`

**Intent**: `get_turn_context` calls `load_turn` on the same cached command instance the route injects as `command` — FastAPI dependency caching (per-request, keyed on the callable) guarantees they're identical, so no second `GenerateReplyCommand`/`UnitOfWork` gets built.

**Contract**:

```python
async def get_turn_context(
    session_id: UUID,
    body: SendMessageRequestDTO,
    command: Annotated[GenerateReplyCommand, Depends(get_generate_reply_command)],
) -> tuple[CaptureSession, MessageContent]:
    return await command.load_turn(SessionId(value=session_id), body.content)
```

Drop the `get_capture_session_repository` import/`Depends` param and the `load_open_session_for_turn` import. The `send_message` route body is unchanged in this phase (error handling lands in Phase 3).

#### 4. Test/composition call sites

**File**: `backend/tests/unit/capture/test_send_message_command.py`

**Intent**: Exercise `load_turn` as a method instead of the deleted free function; behavior (exception types) is unchanged.

**Contract**: `_make_command_stack()` passes `capture_sessions=session_repo` into `GenerateReplyCommand(...)`. The three `test_load_open_session_for_turn_*` tests are renamed `test_load_turn_*` and call `stack.command.load_turn(...)` instead of the free function.

**File**: `backend/tests/integration/support/in_memory_capture.py`

**Intent**: The integration composition's override factory must satisfy the new constructor signature.

**Contract**: `override_generate_reply_command` passes `capture_sessions=composition.capture_sessions` into `GenerateReplyCommand(...)`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/test_send_message_command.py tests/integration/test_capture_http.py -v`

#### Manual Verification:
- `cd backend && uv run fastapi dev src/main.py`, then in another terminal: `curl -s -X POST localhost:8000/capture-sessions/00000000-0000-4000-8000-000000000001/messages -H 'Content-Type: application/json' -d '{"content": "hi"}'` and confirm a clean `404` JSON body with `"code": "capture_session_not_found"` — proving the new `Depends`-cached wiring still produces a pre-stream 4xx.

---

## Phase 2: Remove the R4-F1 staleness re-read in `handle`

### Overview

Drops the in-UoW `capture_sessions.get` re-check that exists only to guard against a stale caller-supplied `session.topic`, and pins the resulting behavior with a new test.

### Changes Required:

#### 1. Simplify topic assignment

**File**: `backend/src/application/capture/commands/send_message.py`

**Intent**: Trust the `session` `load_turn` already loaded; the second read was defending against a race that, under the current shared in-memory repository instance, cannot occur — and once a real adapter lands, the fix belongs at the transaction boundary (row locking), not as a free-standing re-read here.

**Contract**:

```python
if session.topic is None:
    # Deliberately reopens the R4-F1 staleness scenario — see
    # context/archive/changes/2026-08-29-capture-flow-socratic-conversation/reviews/2026-08-31-r4-property-test-phase-6.md.
    # load_turn and this UoW share one in-memory CaptureSessionRepository instance
    # today, so the caller's `session` is never actually stale under that adapter;
    # a real adapter should close this gap with a transaction-boundary lock, not a
    # second free-standing read.
    topic = await self._topic_extraction.extract(content)
    session.assign_topic(topic)
    await uow.capture_sessions.save(session)
else:
    topic = session.topic
```

The `persisted = await uow.capture_sessions.get(session.id)` branch and its `if persisted is not None and persisted.topic is not None` check are deleted.

#### 2. Pin the new behavior

**File**: `backend/tests/unit/capture/test_send_message_command.py`

**Intent**: Make the accepted trade-off an explicit, readable regression test rather than an implicit absence.

**Contract**: New test using the same stale-session construction the archived R4-F1 review proposed, asserting the *opposite* outcome — fresh extraction wins, persisted topic is overwritten:

```python
async def test_generate_reply_reextracts_topic_when_caller_session_is_stale() -> None:
    stack = _make_command_stack()
    session = CaptureSession.start()
    session.assign_topic(Topic(value="Persisted topic"))
    await stack.session_repo.save(session)

    stale = CaptureSession(
        id=session.id, topic=None, status=session.status,
        created_at=session.created_at,
    )
    content = MessageContent(value="0")

    events = [event async for event in stack.command.handle(stale, content)]
    done = next(event for event in events if isinstance(event, ReplyDoneEvent))

    assert done.topic != "Persisted topic"
    persisted = await stack.session_repo.get(session.id)
    assert persisted is not None
    assert persisted.topic is not None
    assert persisted.topic.value == done.topic
```

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/test_send_message_command.py -v`

---

## Phase 3: In-band `CoreException` → `ReplyErrorEvent`

### Overview

Widens the SSE wire contract with an `error` arm and wraps the generator's post-`Depends` work so a `CoreException` raised inside `handle` becomes one clean in-band event instead of a broken stream.

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
    session, content = turn
    try:
        async for event in command.handle(session, content):
            yield event
    except CoreException as exc:
        yield ReplyErrorEvent(code=exc.code(), detail=str(exc))
        return
```

Add `from domain.exceptions import CoreException` and `ReplyErrorEvent` to this file's imports.

#### 3. Regression coverage for the mechanism

**File**: `backend/tests/integration/test_capture_http.py`

**Intent**: Prove a `CoreException` raised mid-`generate()` (i.e. after the 200 has gone out) becomes one `{type: "error", code, detail}` event and a clean stream close — using an existing, already-mapped exception class so the `CoreException` exhaustiveness test (`backend/tests/unit/test_http_error_mapping.py`) needs no change.

**Contract**: A small local `ReplyGenerationPort` test double that yields one chunk then raises (e.g. `CaptureSessionClosedError`), threaded into a `capture_client`-equivalent `TestClient` via `InMemoryCaptureComposition` with `reply_generation` swapped before `dependency_overrides()` is called. Asserts: response status is still `200`; the SSE event list contains exactly one `delta`, then one `error` event carrying the exception's `code()`; no `done` event follows. The two existing pre-stream tests (`test_unknown_session_returns_clean_404_before_streaming`, `test_empty_message_content_returns_clean_422_before_streaming`) must stay green unmodified — they're the proof the split still holds.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/integration/test_capture_http.py tests/unit/capture/test_send_message_command.py tests/unit/test_http_error_mapping.py -v`

---

## Phase 4: TUI `stream.ts` — parse `error` events + richer pre-stream errors

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

## Phase 5: TUI `chat.ts` store — `streamError` state

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

## Phase 6: TUI `CaptureScreen.tsx` — status-bar rendering

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
- Backend: `test_send_message_command.py` covers `load_turn`'s three exception paths (Phase 1) and the new stale-session behavior pin (Phase 2).
- TUI: `stream.test.ts` covers the `error` parse arm and both `SendMessageHttpError` paths (Phase 4); `chat.test.ts` covers `streamError` set/clear from both sources (Phase 5).

### Integration Tests:
- `test_capture_http.py`: existing pre-stream 404/422 tests stay green unmodified; new mid-stream `CoreException` → in-band `error` test (Phase 3).

### Manual Testing Steps:
- Phase 1's curl repro (pre-stream 404 through the new wiring); Phase 6's end-to-end normal-path run (no regression in the built TUI).

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
