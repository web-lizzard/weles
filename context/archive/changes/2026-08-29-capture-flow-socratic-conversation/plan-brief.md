# Capture Flow — Socratic Conversation — Plan Brief

> Full plan: `plan.md`

## What & Why

Realizes slice S-01 of `capture-flow`: a user starts a capture session and the agent probes their understanding through Socratic follow-ups (AC-01–AC-04). Scope includes the full vertical slice — domain, application, HTTP, and the TUI chat screen — with the agent's conversation delivered as a streamed SSE reply.

## Starting Point

Greenfield inside an already-scaffolded hexagonal backend (`domain/`, `application/`, `adapters/` exist with a `CoreException` mechanism and a health route) and a bootstrap-only TUI (`app.tsx` renders a static string; empty Zustand store).

## Desired End State

The TUI opens a session, the user types a message, the agent's reply streams back chunk-by-chunk in the terminal, and the session's topic (derived from that first message, not typed separately) appears alongside it. Subsequent turns continue the same way.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Session-start body | No body; topic derived later | Topic needs message content, which doesn't exist at session-creation time | Plan |
| Endpoint count | 2, not 3 | "Send message" and "get reply" are merged into one streamed call per turn | Plan |
| `CaptureSession.start()` shape | No `topic` param (deviates from ADR) | The id must exist before any topic-bearing content does | Plan |
| Streaming payload | Discriminated union (`delta`/`done`) | One clean place for the canonical final text + topic, not just raw text chunks | Plan |
| SSE mechanism | Native `fastapi.sse.EventSourceResponse` | Installed FastAPI (0.141.1) ships this; no `sse-starlette` needed | Plan (verified in installed source) |
| Agent ports | 3 separate ports (topic/assessment/reply) | Narrow, single-purpose contracts survive an LLM-adapter swap better than one wide port | Plan |
| Agent adapters (this slice) | Deterministic stand-ins | Real `pydantic-ai` deferred; ports must still be genuinely async/streaming-shaped | Plan |
| Value Objects | `Topic`, `MessageContent`, `MessageRole`, `SessionId`, `MessageId`, `ConfidencePoint`/`ConfidenceAssessment` | Port/DTO contracts typed in VOs so they outlive the adapter swap | Plan |
| VO validation mechanism | Manual checks in `model_validator(mode="after")`, never `Field(min_length=/max_length=)` | Pydantic's own field constraints raise `pydantic.ValidationError`, not `CoreException` — silently breaking the error-mapping table | Plan (verified) |
| Turn validation vs. streaming | `load_open_session_for_turn` runs as a `Depends` (no write); `GenerateReplyCommand`'s generator owns the turn's one `UnitOfWork` commit | An exception raised inside an SSE generator body bypasses `add_exception_handler` entirely in the installed FastAPI — verified empirically; a `Depends` is the only point that still maps cleanly | Plan (verified) |
| `CaptureSession` scope | Only `start()`/`assign_topic()`, `open` status | `draft_note`/`approve`/`close` belong to S-04/S-06 | Research |
| TUI state | Zustand, incl. chat/transcript state | Explicit request, despite `tui-stack` scoping Zustand narrower | Plan |
| Auth | None in this slice | Mechanism still undecided by `repo-shape`; nothing here should block that later decision | Plan |

## Scope

**In scope:** Domain (`CaptureSession`, `Message`, 5 Value Objects), application layer (2 commands, 1 query, 3 agent ports + in-memory stand-ins, `UnitOfWork`), 2 HTTP endpoints, BDD coverage for AC-01–04, TUI chat screen with SSE streaming.

**Out of scope:** Real LLM adapter, `Note`/`Topic`/`Tag` aggregates, session persistence/resume, auth, `ConfidenceAssessment` surfaced in the UI, mutation/property testing.

## Architecture / Approach

`POST /capture-sessions` creates a topic-less session. `POST /capture-sessions/{id}/messages` does everything else: records the user message, derives+assigns the topic on turn one only, pulls the transcript via a query port, runs assessment → reply-generation, and streams the reply as SSE deltas plus one terminal `done` event carrying the canonical text and current topic.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1–2 | Domain: VOs, `CaptureSession`, `Message` | Getting the `topic: Topic \| None` + `assign_topic` guard right |
| 3–4 | Application ports + in-memory adapters (incl. stand-ins) | Stand-in adapters must be deterministic yet genuinely satisfy AC-03/04 |
| 5–6 | Commands (`StartCaptureSession`, `load_open_session_for_turn` + `GenerateReplyCommand`) | Commit-after-stream-drains + rollback-on-cancel via `InMemoryUnitOfWork`, exactly one commit per turn |
| 7–8 | HTTP adapter, SSE wiring | `openapi-typescript` may not parse the SSE `itemSchema` cleanly |
| 9 | BDD for AC-01–04 | — |
| 10–11 | TUI data layer (SSE client, Zustand store) | Hand-rolled SSE parsing correctness |
| 12–13 | TUI chat screen | `<Static>` misuse (mutating already-rendered items) |

**Prerequisites:** None beyond what's already scaffolded.
**Estimated effort:** Large — 13 phases across three layers and two runtimes.

## Open Risks & Assumptions

- `Topic` (≤200 chars) and `MessageContent` (≤4000 chars) length caps are this plan's own assumption, not sourced from any PRD/ADR.
- `openapi-typescript@^7` may not parse the OpenAPI 3.2 SSE `itemSchema` FastAPI emits — Phase 10 verifies this directly and falls back to hand-maintained TS types if not.
- `CaptureSessionClosedError`'s guard is unreachable by any AC in this slice (no `close()` exists yet) — kept anyway per explicit instruction, tested via a fixture that bypasses the normal factory.
- Discipline risk: it's easy to reach for `Field(min_length=/max_length=)` on a VO instead of a manual `model_validator` check — the former silently produces `pydantic.ValidationError` instead of a `CoreException`. Mitigated by making every VO test assert the exact exception type, not just "raises."

## Success Criteria (Summary)

- BDD suite green for AC-01–AC-04.
- A user can run the built TUI CLI against the running backend and hold a multi-turn conversation with a streamed, topic-labeled reply.
- Every new port has a passing contract-test suite against its in-memory adapter.
