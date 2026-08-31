---
date: 2026-08-31T12:44:00+02:00
topic: "Move turn-guard errors off Depends into the SSE stream — conventions and whether the guard survives I/O-bound adapters"
topic_slug: null
container_id: capture-flow-socratic-conversation-send-mesage-refactor
tags: [research, capture-flow, sse, error-handling, fastapi, http-streaming]
last_updated: 2026-08-31
---

# Research: Move turn-guard errors off Depends into the SSE stream

## Research Question

Chciałbym dorzucić frame do tej zmiany - mianowicie zależy mi na tbym aby usunąc tę metodę robiącą checki w depends. Uważam, że ta metoda i tak nieprzetrwa jak dojdą adaptery I/o bound.  przenieśc obsługę błędów do streamu, sprawdź w sieci jakie są konwencje na obsługę błędów tego typu w http stream

## Summary

`load_open_session_for_turn` (wired as `Depends(get_turn_context)`) exists so `CoreException`s raised *before* FastAPI commits a 200 `text/event-stream` still become JSON 4xx via `core_exception_handler`. That still holds on installed FastAPI 0.141.1: an async generator route with `response_class=EventSourceResponse` builds the `StreamingResponse` after Depends, without running the generator body — so a raise inside `GenerateReplyCommand.handle` cannot change the status and is not seen by `add_exception_handler`.

The claim that this Depends check "will not survive I/O-bound adapters" is only half true. An async SQL `CaptureSessionRepository.get` *inside Depends* still produces a clean 4xx. What actually breaks when real adapters land is everything *after* the 200 is committed: `ReplyGenerationPort.generate` failing mid-chunk, `TopicExtractionPort.extract` I/O, `UnitOfWork.commit` I/O, and the Depends `get()` sitting outside the turn's UoW (TOCTOU / double-read). Today's generator is "exception-free by construction" only because the stand-in adapters do not fail.

HTTP/SSE convention, as documented by Anthropic, OpenAI, Gemini, and FastAPI maintainers, is a **split**, not "put every error in the stream":

- Errors known before any byte (404, 422, 409, auth) → HTTP 4xx/5xx JSON; do not start `text/event-stream`.
- Errors after headers are flushed (upstream LLM, timeout, abort) → keep 200, yield an in-band error event, then `return` (do not re-raise).

Collapsing 404/validation into a 200 SSE error event is not a WHATWG or LLM-API convention; it is a workaround for starting the stream too early. WHATWG `EventSource.onerror` is a connection failure, not an application payload. This TUI uses `fetch()`, so it *can* read a 4xx body — and today it already branches on `!response.ok` before parsing SSE, without distinguishing 404/422/409.

Implication for a new frame on this change: keep pre-stream HTTP mapping for the current Depends failures; add an in-band `error` arm to `ReplyStreamEvent` for failures that can only happen after 200. Deleting Depends without a non-generator wrapper forces those 404/422 onto the 200+event path and rewrites the integration tests that lock clean 404/422. The FastAPI-documented alternative that removes Depends *and* keeps 4xx is a regular coroutine that validates, then `return EventSourceResponse(agen)` — that fights the native generator+`itemSchema` route shape currently used.

## Findings

### Why Depends exists (and still does)

- `get_turn_context` is the HTTP wrapper that calls `load_open_session_for_turn` and is injected into the SSE route — `backend/src/adapters/http/capture.py:32-43`, `:59-65`.
- `load_open_session_for_turn` builds `MessageContent` (empty/too-long → 422), `get`s the session (`None` → 404), and rejects non-`OPEN` (409). No UoW, no write — `backend/src/application/capture/commands/send_message.py:26-37`.
- `GenerateReplyCommand.handle` assumes that pair is already valid and owns the single UoW, topic assignment, generate/stream, and commit — `backend/src/application/capture/commands/send_message.py:55-95`.
- Archived plan Critical Implementation Details: exceptions inside an `EventSourceResponse` generator (before or after first `yield`) become an unhandled `ExceptionGroup` and bypass `add_exception_handler`; Depends exceptions still map to 4xx — `context/archive/changes/2026-08-29-capture-flow-socratic-conversation/plan.md:25`, `:61`, `:451`.
- Installed FastAPI 0.141.1 still matches that claim: `is_sse_stream` is "generator + EventSourceResponse"; `solve_dependencies` runs first; `dependant.call(**values)` only *creates* the generator; `_producer` iterates it after `StreamingResponse` is constructed — `backend/.venv/lib/python3.12/site-packages/fastapi/routing.py:481-646`, `:1071-1077`. Same mechanics quoted against 0.141.0 in FastAPI discussion 15129.

### What I/O-bound adapters actually break

- Depends *can* await. `get_turn_context` / `load_open_session_for_turn` are already `async`. A SQL `get()` there still raises `CoreException` before 200.
- Compose already shares one `InMemoryCaptureSessionRepository` between Depends and each fresh `InMemoryUnitOfWork` — `backend/src/adapters/compose.py:30-66`. The structural problem is not a second store; it is that Depends `get()` is **outside** the turn UoW. Between Depends success and `async with self._uow`, another writer can close/delete/change topic.
- A second `get` already exists inside `handle` for the R4-F1 stale-topic guard — `backend/src/application/capture/commands/send_message.py:64-72`.
- Failures that only appear with real adapters, all past Depends: `topic_extraction.extract`, `transcript_query`, `confidence_assessment.assess` (before first delta); `reply_generation.generate` mid-chunk (after some deltas); `uow.commit()` (after generate, before `done`). Deterministic adapters have no failure paths.
- Hexagonal rule: only the input adapter maps `CoreException.code()` → transport. Raising inside the generator keeps ownership but FastAPI cannot apply `EXCEPTION_STATUS_MAP`. Yielding a DTO error event is still adapter-owned encoding of an application DTO, not a layering violation — but it abandons HTTP status for those codes — `context/adrs/hexagonal-arch-shape/decision.md:35`, `:67`; `backend/src/adapters/http/errors.py:6-23`.

### Current stream contract and client

- Wire union is `delta` | `done` only — `backend/src/application/capture/dto.py:15-29`. TUI mirror the same two arms — `tui/src/api/stream.ts:10-22`. No error event exists.
- TUI `sendMessage` throws on `!response.ok` with the status number only; body/`code` ignored; 404/422/409 not distinguished — `tui/src/api/stream.ts:45-47`. `chat.ts` has no `catch`; the user line is appended before the try — `tui/src/store/chat.ts:38-62`. `CaptureScreen` fire-and-forgets submit — `tui/src/screens/CaptureScreen.tsx:35-41`.
- Generated OpenAPI types `text/event-stream` as `unknown`; documented 422 is FastAPI's `HTTPValidationError`, not `{code, detail}` — `tui/src/api/generated/schema.d.ts:185-204`. `tui-stack` requires a hand-written fetch/ReadableStream client and does not discuss stream vs HTTP errors — `context/adrs/tui-stack/decision.md:18-20`.
- Integration tests that lock "error as HTTP, not SSE": `test_unknown_session_returns_clean_404_before_streaming`, `test_empty_message_content_returns_clean_422_before_streaming` — `backend/tests/integration/test_capture_http.py:84-107`. No HTTP test for 409 on this route (closed session is unit-tested as `CaptureSessionClosedError` only — `backend/tests/unit/capture/test_send_message_command.py:58-73`).

### HTTP / SSE conventions (web)

- WHATWG SSE has fields `event`/`data`/`id`/`retry` only; no reserved application-error event. `EventSource.onerror` fires when the connection fails to open or is failed/reestablished — not an application payload. EventSource requires HTTP 200 + `text/event-stream`; any other status fails the connection and drops the body — <https://html.spec.whatwg.org/multipage/server-sent-events.html>, <https://developer.mozilla.org/en-US/docs/Web/API/EventSource/error_event>.
- HTTP status lives in the start-line; it cannot change after `http.response.start`. Trailers are not a new status code and browsers/Fetch/EventSource do not expose them (except `Server-Timing`) — RFC 9110/9112; <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Trailer>.
- Anthropic documents the split explicitly: standard HTTP error JSON until 200; after 200, "error handling doesn't follow these standard mechanisms" and an SSE `event: error` is used (e.g. `overloaded_error`, which would be HTTP 529 non-streaming). 404 remains `not_found_error` JSON, not an SSE event — <https://docs.anthropic.com/en/api/errors>, <https://docs.anthropic.com/en/api/messages-streaming>.
- OpenAI: HTTP status table for auth/rate-limit/server errors; Chat Completions mid-stream uses `data: {"error": {...}}` (SDK raises if `data.get("error")`); Responses API adds typed `type: "error"` / `response.failed` events — <https://developers.openai.com/api/docs/guides/error-codes>, <https://developers.openai.com/api/docs/guides/streaming-responses>.
- Gemini: failed `GenerateContent` sets HTTP 400/403/429 and returns `{error:{code,message,status}}`. Streaming docs describe SSE chunks of `GenerateContentResponse`, not `event: error` — <https://ai.google.dev/gemini-api/docs/generate-content/api-errors>.
- FastAPI official SSE tutorial shows `yield` + `EventSourceResponse`; it does **not** document generator exceptions. Collaborator (YuriiMotov, discussion 11471): exception handlers cannot rewrite headers after streaming has started; wrap the generator in try/except and send the error as a stream chunk. Discussion 15129: raise `HTTPException` before constructing the stream (Depends, or a non-yielding coroutine that then `return EventSourceResponse(...)`); after the first yield, only in-band events work. Repro on 0.141.0: `raise HTTPException(403)` before `yield` still produces `200` with empty body. `EventSourceResponse` is a marker class — no exception-to-event hook — <https://fastapi.tiangolo.com/tutorial/server-sent-events/>, <https://github.com/fastapi/fastapi/discussions/15129>, <https://github.com/fastapi/fastapi/discussions/11471>.
- sse-starlette's official advanced example: yield `{event: "error", data: ...}` then `return` so the generator closes cleanly (`more_body: False`). Re-raising truncates the stream with no explanation — <https://github.com/sysid/sse-starlette/blob/main/examples/04_advanced_features.py>.
- OpenAPI 3.2 `itemSchema` + `oneOf` can include an `event: error` variant; FastAPI does not generate that discriminated union automatically. 3.1 has no `itemSchema` keyword — <https://spec.openapis.org/oas/v3.2.0.html>.

### Frame options this evidence supports

1. **Keep Depends for 404/422/409; add in-band error events for post-200 failures** (LLM, extract, commit). Matches Anthropic/OpenAI/Gemini/FastAPI split. Smallest contract change: widen `ReplyStreamEvent`, try/except in the generator (or adapter) then `return`, teach TUI `parseStreamEvent` an `error` arm. Integration 404/422 tests stay.
2. **Delete Depends, fold guards into `handle`, always-200 + error event for everything.** Matches the user's stated preference. Contradicts the documented split; rewrites `test_capture_http.py:84-107`; TUI already treats any `!ok` as a throw, so it would instead see 200 and must handle `type: "error"`. Hexagonal mapping table stops applying to these codes on this route.
3. **Delete Depends *and* keep HTTP 4xx** by changing the route from an async-generator endpoint to a coroutine that runs the guards, then `return EventSourceResponse(command.handle(...))`. Named as a workaround in FastAPI discussion 15129. Conflicts with native FastAPI SSE detection (`is_sse_stream = is_generator and EventSourceResponse`), which is how this slice gets OpenAPI `itemSchema` today.

Option 1 is the one the web evidence calls conventional. Option 2 is the one that literally "moves error handling into the stream." Option 3 is the only way to drop the Depends *function* without dropping HTTP 4xx.

## Code References

- `backend/src/application/capture/commands/send_message.py:26-37` — `load_open_session_for_turn` (content + session guards, no UoW)
- `backend/src/application/capture/commands/send_message.py:55-95` — `GenerateReplyCommand.handle` streaming body and commit
- `backend/src/application/capture/commands/send_message.py:64-72` — in-handle `capture_sessions.get` (R4-F1), second read after Depends
- `backend/src/adapters/http/capture.py:32-43` — `get_turn_context` Depends wrapper
- `backend/src/adapters/http/capture.py:55-65` — SSE route, generator body is only `async for`/`yield`
- `backend/src/adapters/http/errors.py:6-23` — `EXCEPTION_STATUS_MAP` and `core_exception_handler` JSON 4xx
- `backend/src/adapters/compose.py:30-66` — shared in-memory session repo; fresh UoW per command
- `backend/src/application/capture/dto.py:15-29` — `ReplyStreamEvent` = `delta` | `done`
- `backend/src/main.py:8-11` — `add_exception_handler(CoreException, ...)`
- `backend/tests/integration/test_capture_http.py:84-107` — 404/422 locked as HTTP, not SSE
- `backend/tests/unit/capture/test_send_message_command.py:47-82` — `load_open_session_for_turn` exact exception types
- `tui/src/api/stream.ts:10-22` — TUI event union, two arms
- `tui/src/api/stream.ts:45-47` — `!response.ok` throw, status only
- `tui/src/store/chat.ts:38-62` — no catch; optimistic user line
- `context/archive/changes/2026-08-29-capture-flow-socratic-conversation/plan.md:25,61,451` — why Depends was required
- `context/adrs/hexagonal-arch-shape/decision.md:35,67` — input adapter owns `code` → transport mapping
- `backend/.venv/lib/python3.12/site-packages/fastapi/routing.py:481-646,1071-1077` — SSE 200 committed before generator iteration

## External References

- <https://html.spec.whatwg.org/multipage/server-sent-events.html> — SSE fields; EventSource requires 200 + `text/event-stream`; `error` event is reconnect/fail
- <https://developer.mozilla.org/en-US/docs/Web/API/EventSource/error_event> — "`error` event … fired when a connection with an event source fails to be opened"
- <https://docs.anthropic.com/en/api/errors> — HTTP error catalog; streaming: errors after 200 "don't follow these standard mechanisms"
- <https://docs.anthropic.com/en/api/messages-streaming> — `event: error` / `overloaded_error` mid-stream
- <https://developers.openai.com/api/docs/guides/error-codes> — HTTP 401/429/500/503 for request failures
- <https://developers.openai.com/api/docs/guides/streaming-responses> — Responses API `error` / `response.failed` events
- <https://ai.google.dev/gemini-api/docs/generate-content/api-errors> — failed generate sets HTTP status + `{error:{code,message,status}}`
- <https://fastapi.tiangolo.com/tutorial/server-sent-events/> — official `yield` + `EventSourceResponse`; no generator-exception guidance
- <https://github.com/fastapi/fastapi/discussions/15129> — generator commits 200 before first `__anext__`; Depends or `return EventSourceResponse(...)` for HTTP errors
- <https://github.com/fastapi/fastapi/discussions/11471> — exception handlers cannot rewrite headers after streaming starts; try/except and send error as a chunk
- <https://github.com/sysid/sse-starlette/blob/main/examples/04_advanced_features.py> — yield `event: error` then `return`
- <https://www.rfc-editor.org/rfc/rfc9110.html> — status in start-line; trailers are not response controls
- <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Trailer> — browsers do not expose trailers via Fetch/XHR
- <https://spec.openapis.org/oas/v3.2.0.html> — `itemSchema` applied per stream item; `oneOf` for typed SSE events

## Open Questions

- Whether this change's new frame keeps HTTP 4xx for the current Depends failures (option 1 or 3) or deliberately adopts always-200 in-band errors for 404/422/409 as well (option 2).
- Whether FastAPI native SSE `itemSchema` generation is still required if the route stops being a generator (option 3).
- In-band event shape: Anthropic-style `event: error` + nested error object, OpenAI Chat Completions `data: {"error": ...}`, or a third `ReplyStreamEvent` arm `{type: "error", code, detail}` matching `EXCEPTION_STATUS_MAP` codes — TUI currently parses only `data:` JSON with a `type` discriminator.
