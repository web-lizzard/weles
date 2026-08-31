# Frame: Turn loading vs in-band stream errors

## Problem

`POST /capture-sessions/{session_id}/messages` is a FastAPI native SSE generator (`response_class=EventSourceResponse`). FastAPI commits `200` + `text/event-stream` after Depends resolution and *before* the generator body runs. `add_exception_handler` therefore cannot map `CoreException`s raised inside `GenerateReplyCommand.handle` to HTTP 4xx.

Today that is papered over by a free function, `load_open_session_for_turn`, wired as `Depends(get_turn_context)`: it constructs `MessageContent`, loads the session, and rejects missing/closed sessions so those failures still become JSON 404/422/409. The generator is then "exception-free by construction" only because the stand-in adapters never fail.

That split is the wrong *ownership* (a free function next to the command, a second session `get` outside the turn's `UnitOfWork`) but the right *timing*. Folding the same work into the generator "before the first yield" does not preserve HTTP 4xx — the yield has not run, but the 200 has already gone out. I/O-bound adapters (SQL `commit`, real `ReplyGenerationPort.generate`, `TopicExtractionPort.extract`) will fail *after* that 200; Depends cannot see them.

## Decision

Keep the HTTP / SSE split that Anthropic, OpenAI, Gemini, and FastAPI maintainers document:

1. **Errors known before any stream byte** (unknown session, closed session, empty/too-long content) stay **HTTP 4xx JSON** via `core_exception_handler`. Do not start `text/event-stream` for them.
2. **Errors after headers are flushed** (generate mid-chunk, extract/assess I/O, `uow.commit` I/O) stay on HTTP 200 and are reported **in-band**, then the generator `return`s — it does not re-raise.

Move the pre-stream work onto `GenerateReplyCommand` as a second method, **`load_turn`**. It is not a guard/validator: on success it returns the `(CaptureSession, MessageContent)` pair `handle` consumes; on failure it raises the same `CoreException`s as today (`CaptureSessionNotFoundError`, `CaptureSessionClosedError`, `EmptyMessageContentError`, `MessageContentTooLongError`).

**Call site stays in Depends** (the HTTP wrapper may keep the name `get_turn_context`). `load_turn` must run during `solve_dependencies`, before FastAPI constructs the generator. It must not run inside the generator body, including on a line "above" `yield`. It must not use the turn's `UnitOfWork` — that UoW starts when `handle` starts.

In-band failures become a third arm of `ReplyStreamEvent`: `{type: "error", code, detail}`, using the same `code` strings `EXCEPTION_STATUS_MAP` already knows. The TUI already parses `data:` JSON with a `type` discriminator; it does not read the SSE `event:` field. After an `error` event the stream ends. The TUI still treats `!response.ok` as the pre-stream 4xx path.

## Why `load_turn`

Rejected: `guard` / `validate` — the success path returns domain values, not a boolean, and constructing `MessageContent` plus loading an open session is intake, not a check.

`load_turn(session_id, raw_content) -> tuple[CaptureSession, MessageContent]` keeps the verb from today's `load_open_session_for_turn`, drops the free-function length, and pairs with `handle` as load-then-run.

## Out of scope

- Collapsing 404/422/409 into a 200 SSE error event.
- Changing the route from an async-generator endpoint to `return EventSourceResponse(...)` solely to drop Depends (that fights native SSE `itemSchema` detection).
- Real SQL / LLM adapters — this change only makes their failures reportable.
- `EventSource.onerror` as an application-error channel (it is a connection failure).
- HTTP trailers as an error channel (browsers/Fetch do not expose them).

## Success

- Unknown session and empty content still produce clean HTTP 404/422 JSON, not a broken or 200 stream. Closed session remains HTTP 409 on the same path.
- `GenerateReplyCommand.load_turn` is the only pre-stream loader; the free function `load_open_session_for_turn` is gone.
- A failure inside `handle` after 200 yields one `type: "error"` event and a clean generator close, not an `ExceptionGroup` / truncated stream.
- TUI distinguishes pre-stream `!response.ok` from an in-band `error` event.
