# Capture Flow Send-Message Refactor: `guard_session` + Self-Loading `handle` + In-Band Stream Errors — Plan Brief

> Full plan: `plan.md`
> Revision 1 (2026-08-31): `load_turn`'s return-a-`CaptureSession` design replaced by `guard_session` (validates, returns only `MessageContent`) + `handle(session_id, content)` self-loading its own session. See `plan.md`'s revision note and `plan-versions/v1-plan-brief.md` for the prior version.

## What & Why

The pre-stream session/content guard for `POST /capture-sessions/{id}/messages` lives as a free function beside `GenerateReplyCommand` instead of on it. This plan moves it onto the command as `guard_session` (still called from `Depends`, so it keeps producing clean HTTP 4xx), and changes `handle` to load its own session rather than trust a caller-supplied one — which structurally eliminates the R4-F1 staleness bug instead of relying on either a shared in-memory reference or a deliberately-reopened gap. It also adds an in-band `error` event to the SSE stream so a `CoreException` raised after the 200 is committed reaches the client instead of breaking the stream.

## Starting Point

`load_open_session_for_turn` + `Depends(get_turn_context)` handle 404/422/409 today; `GenerateReplyCommand.handle` takes the caller-supplied session on faith and has no failure path of its own because its adapters are all deterministic stand-ins. A defensive re-read (R4-F1) exists inside `handle` to guard against a caller-supplied stale session — but it's a patch, not a structural fix.

## Desired End State

`guard_session` is the only pre-stream check, invoked from `Depends` via FastAPI's per-request dependency caching so it shares the exact `GenerateReplyCommand` instance `handle` uses. `handle(session_id, content)` loads its own `CaptureSession` fresh, in its own transaction, and re-validates existence/open-status itself — R4-F1 can no longer be expressed, and the rare TOCTOU window between `guard_session` and `handle` now raises there, surfacing as an in-band `{type: "error", code, detail}` SSE event instead of misbehaving. The TUI shows both error sources as a status-bar notification that clears on the next send.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Keep pre-stream HTTP 4xx vs. always-200 | Split kept: `Depends` for known-before-any-byte errors, in-band event for post-200 | Matches Anthropic/OpenAI/Gemini/FastAPI-maintainer convention; collapsing it would rewrite the locked 404/422 integration tests and lose standard HTTP status semantics for every future client | Plan (interview) |
| `guard_session`'s call site | Stays in `Depends`, resolved via FastAPI's per-request dependency cache | A `raise` inside the route's own generator body — even before the first `yield` — is already too late; 200 is already committed | Frame |
| Does `guard_session` return a `CaptureSession`? | No — only `MessageContent`. `handle` loads its own session by id. | Loading a session in Depends is a check whose value would be stale by the time a real adapter needs to lock it anyway; `content` is genuine intake and stays returned | Plan (interview) |
| R4-F1 staleness scenario | Structurally eliminated, not deliberately reopened — `handle` no longer accepts a caller-supplied `CaptureSession` at all | A prior revision planned to delete the in-UoW re-check and accept the regression; reconsidered once the design showed the bug can be removed by construction instead | Plan (interview, revised) |
| Non-`CoreException` failures in the generator | Not caught — still propagate as today's broken-stream behavior | Adapters are expected to raise `CoreException` subclasses for their own failures | Plan (interview) |
| TUI error surfacing | Dedicated status-bar/toast component, not an inline chat message | Keeps transport errors visually separate from conversation content | Plan (interview) |

## Scope

**In scope:** `GenerateReplyCommand.guard_session` + self-loading `handle`; `ReplyErrorEvent` wire arm; generator `CoreException` handling; TUI parsing, store state, and status-bar rendering for both error sources.

**Out of scope:** Real SQL/LLM adapters; real row-level locking inside `handle`'s transaction; collapsing 404/422/409 into a 200 stream; a toast library or timer-based auto-dismiss.

## Architecture / Approach

Backend phases (1-2) land first and each leaves the suite green — `guard_session` + self-loading `handle`, then the error DTO/generator change. TUI phases (3-5) then move outward from parser → store → rendered component, one file/concern per phase, matching the existing test layout. The backend restructuring is invisible to the TUI — the wire contract those phases depend on is unchanged by the revision.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. `guard_session` + self-loading `handle` | Command owns the pre-stream check; `handle` is self-sufficient, R4-F1 eliminated by construction | Missing a call site still importing the deleted free function or the old `handle(session, ...)` signature |
| 2. In-band `CoreException` → event | Post-200 failures (including `handle`'s own new guard) become one clean event, not a broken stream | Test needs a real mid-stream failure without a working real adapter — uses a small test double |
| 3. TUI `stream.ts` | Parses `error`; typed, richer pre-stream error | None significant |
| 4. TUI `chat.ts` store | Single `streamError` field from both sources | Silently swallowing an error meant to reach the UI |
| 5. TUI `CaptureScreen.tsx` | Status-bar rendering | Can't manually trigger the error path — no real failing adapter exists yet |

**Prerequisites:** None — no upstream change blocks this.
**Estimated effort:** 5 phases, all single-pass TDD (no stub/behavior split needed anywhere).

## Open Risks & Assumptions

- `handle`'s own guard doubles the read count versus the pre-revision design (one cheap check in `Depends`, one authoritative check+load in `handle`) — accepted as the correct shape for a fast-fail-then-load-for-write pattern, not a cost to optimize away.
- Phase 5's error path can only be exercised through automated test doubles today — no real adapter fails, so there's no way to manually trigger it end-to-end yet.

## Success Criteria (Summary)

- Unknown/closed session and invalid content still produce clean 404/409/422 JSON before any stream byte.
- A `CoreException` raised inside `handle` after 200 — including its own guard — yields one `error` event and a clean close.
- The free function `load_open_session_for_turn` is gone; `handle` no longer accepts a caller-supplied `CaptureSession`; R4-F1 is structurally unrepresentable.
- The TUI distinguishes and surfaces both error sources via one status-bar notification.
