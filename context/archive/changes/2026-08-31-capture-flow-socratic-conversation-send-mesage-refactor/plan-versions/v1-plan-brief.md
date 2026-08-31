# Capture Flow Send-Message Refactor: `load_turn` Ownership + In-Band Stream Errors — Plan Brief

> Full plan: `plan.md`

## What & Why

The pre-stream session/content guard for `POST /capture-sessions/{id}/messages` lives as a free function beside `GenerateReplyCommand` instead of on it. This plan moves it onto the command as `load_turn` (still called from `Depends`, so it keeps producing clean HTTP 4xx), and adds an in-band `error` event to the SSE stream so a `CoreException` raised after the 200 is committed — which will start happening once real I/O-bound adapters land — reaches the client instead of breaking the stream.

## Starting Point

`load_open_session_for_turn` + `Depends(get_turn_context)` handle 404/422/409 today; `GenerateReplyCommand.handle` assumes valid input and has no failure path of its own because its adapters are all deterministic stand-ins. A leftover defensive re-read (R4-F1) exists inside `handle` to guard against a caller-supplied stale session.

## Desired End State

`load_turn` is the only pre-stream loader, invoked from `Depends` via FastAPI's per-request dependency caching so it shares the exact `GenerateReplyCommand`/`UnitOfWork` instance `handle` uses — no second construction. A `CoreException` raised inside `handle` post-200 becomes one `{type: "error", code, detail}` SSE event, then the stream closes cleanly. The TUI shows that (and a pre-stream 4xx) as a status-bar notification that clears on the next send.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Keep pre-stream HTTP 4xx vs. always-200 | Split kept: `Depends` for known-before-any-byte errors, in-band event for post-200 | Matches Anthropic/OpenAI/Gemini/FastAPI-maintainer convention; collapsing it would rewrite the locked 404/422 integration tests | Research |
| `load_turn` call site | Stays in `Depends`, resolved via FastAPI's per-request dependency cache | A `raise` inside the route's own generator body — even before the first `yield` — is already too late; 200 is already committed | Frame |
| Non-`CoreException` failures in the generator | Not caught — still propagate as today's broken-stream behavior | Your call: adapters are expected to raise `CoreException` subclasses for their own failures | Plan (interview) |
| R4-F1 in-UoW staleness re-read | Removed, with a new test pinning the new behavior | Your call: it's a no-op under the current shared in-memory repository instance; a real adapter should fix this with transaction-boundary locking instead, likely once Postgres lands | Plan (interview) |
| TUI error surfacing | Dedicated status-bar/toast component, not an inline chat message | Your call: keeps transport errors visually separate from conversation content | Plan (interview) |

## Scope

**In scope:** `GenerateReplyCommand.load_turn`; `ReplyErrorEvent` wire arm; generator `CoreException` handling; removing the R4-F1 re-read + its regression pin; TUI parsing, store state, and status-bar rendering for both error sources.

**Out of scope:** Real SQL/LLM adapters; the transaction-boundary locking that eventually replaces R4-F1's protection; collapsing 404/422/409 into a 200 stream; a toast library or timer-based auto-dismiss.

## Architecture / Approach

Backend phases (1-3) land first and each leaves the suite green — `load_turn` + wiring, then the R4-F1 removal, then the error DTO/generator change. TUI phases (4-6) then move outward from parser → store → rendered component, one file/concern per phase, matching the existing test layout.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. `load_turn` ownership + wiring | Command owns the pre-stream load; `Depends` caching shares one instance | Missing a call site still importing the deleted free function |
| 2. Remove R4-F1 re-read | Simpler `handle`, new test pins the accepted trade-off | Silently reopening a bug without a readable trail — mitigated by the comment + test |
| 3. In-band `CoreException` → event | Post-200 failures become one clean event, not a broken stream | Test needs a real mid-stream failure without a working real adapter — uses a small test double |
| 4. TUI `stream.ts` | Parses `error`; typed, richer pre-stream error | None significant |
| 5. TUI `chat.ts` store | Single `streamError` field from both sources | Silently swallowing an error meant to reach the UI |
| 6. TUI `CaptureScreen.tsx` | Status-bar rendering | Can't manually trigger the error path — no real failing adapter exists yet |

**Prerequisites:** None — no upstream change blocks this.
**Estimated effort:** 6 phases, all single-pass TDD (no stub/behavior split needed anywhere).

## Open Risks & Assumptions

- Removing the R4-F1 guard assumes the in-memory adapter's shared-reference behavior continues to hold until a real adapter lands; that real adapter is expected to reintroduce equivalent safety via locking, not a re-read.
- Phase 6's error path can only be exercised through automated test doubles today — no real adapter fails, so there's no way to manually trigger it end-to-end yet.

## Success Criteria (Summary)

- Unknown/closed session and invalid content still produce clean 404/409/422 JSON before any stream byte.
- A `CoreException` raised inside `handle` after 200 yields one `error` event and a clean close.
- The free function `load_open_session_for_turn` and the R4-F1 re-read are both gone, each replaced by an explicit, tested, documented decision.
- The TUI distinguishes and surfaces both error sources via one status-bar notification.
