# Reshape and Approve the Draft into the Outbox — Plan Brief

> Full plan: `plan.md`

## What & Why

Slice S-06 closes the capture loop. The draft note S-04 produces becomes something the user can push back on conversationally and then deliberately hand over: an explicit `/approve` approves the note, closes the session, and drops a `note_approved` envelope into a shared outbox in one transaction. A background worker running in the API's own event loop claims that envelope and processes it, proving the consumer chain before `distill` exists.

## Starting Point

Capture runs end to end up to a persisted `draft` note with a reconciled topic and tags. `Note` has no mutators and no `approve()`, `CaptureSession` has no `close()`, `domain/shared/` does not exist, and nothing in the codebase runs in the background — `main.py` has no lifespan handler at all.

## Desired End State

The user reshapes the draft by describing changes in plain language — the same `Note` row comes back mutated, as often as they like. Typing `/approve` flips the note to `approved` and the session to `closed`, enqueues the envelope atomically, and replaces the draft panel with a confirmation the user cannot type past. The worker claims the envelope within a poll interval, the stub handler logs it, and it settles as `consumed` — visible at `GET /_outbox` outside production.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Outbox port shape | Split `OutboxAppender` / `OutboxClaimer` | Producer and consumer have incompatible transaction stories, so one wide port would hand producers claim methods they must never call. | Plan |
| Envelope lifecycle | Domain methods on `OutboxEnvelope` | Keeps the retry cut-off and transition guards inheritable by any future adapter instead of reimplemented per store. | Plan |
| Enqueue atomicity | Member of capture's `UnitOfWork` | Note, session and envelope commit together, so a failure leaves no half-approved state. | Duck `outbox-shared` |
| Payload shape | Denormalized `note_approved` snapshot | The outbox is the module-isolation boundary; a consumer reaching back into capture's repos would defeat it. | Duck `outbox-shared` |
| Redraft interface | Same `POST /messages`, mutate in place | FR-012 makes reshaping conversational and rules out a second interaction mode. | Frame + Plan |
| Approval interface | Explicit `POST /capture-sessions/{id}/approval` | Keeps model judgment out of an irreversible write, making the PRD guardrail a transport property rather than a prompt hope. | Plan |
| TUI gesture | `/approve` intercepted client-side | Deterministic exact-literal match, no focus juggling, no new input mode. | Plan |
| Worker topology | `asyncio.Task` in FastAPI lifespan | One process, no broker — the cheap-VPS constraint; `run_once()` stays public so tests need no I/O or sleeps. | Duck `overview-thougts` + Plan |
| Claim semantics | Atomic claim, no lease | Mirrors `SELECT ... FOR UPDATE SKIP LOCKED` so the contract test survives the SQL move; lease/reclaim stays parked. | Duck `outbox-shared` + Plan |
| Failure policy | Retry to `max_attempts`, then `failed` | Gives the already-settled `attempts` field its purpose and cuts off poison envelopes. | Plan |
| Debug endpoint | `GET /_outbox`, absent on production | On prod the route does not exist rather than being merely undocumented; on local/staging it is a normal documented route. | Plan |
| Handler for now | `LoggingNoteSaveHandler` | Proves claim → handle → ack end to end; deliberately trivial and expected to be replaced by `distill`. | Plan |
| Envelope `type` shape | `EnvelopeType` VO (`name` + `version`, default `1`) | Structures the "mint a new type" schema-drift story instead of leaving it a bare-string convention; costs nothing extra for today's version-1 types. | Revision 1 |

## Scope

**In scope:** `domain/shared/outbox/` (model, exceptions, both ports); `NoteApprovedPayload` in `domain/capture/`; in-memory store, appender, claimer and their contract suite; `UnitOfWork` gaining `outbox` with rollback coverage; `Note` mutators and `approve()`; `CaptureSession.approve()`/`close()`; the redraft branch; `ApproveNoteCommand`; approval endpoint; private `/_outbox` with its query side; `OutboxWorker`, `OutboxHandler`, stub handler, lifespan task and logging; TUI `/approve` and terminal state; acceptance scenarios for AC-12–AC-15.

**Out of scope:** SQL/Postgres adapter; lease and reclaim; a real `distill` consumer; a second envelope producer; reading notes back; starting a new session from the TUI after approval; the `hexagonal-arch-shape` ADR amendment for the `domain/shared/` bucket; the `discarded` transition.

## Architecture / Approach

```
POST /messages ──► GenerateReplyCommand ──► draft_note()  (first drafting turn)
                                        └─► Note mutators (every later turn)

POST /{id}/approval ──► ApproveNoteCommand
                          session.approve(note) → note.approve() + session.close()
                          uow.notes / uow.capture_sessions / uow.outbox.append(...)
                          ──── one commit ────

lifespan asyncio.Task ──► OutboxWorker.run_forever
                            claimer.claim(type, limit, worker_id)   ← atomic
                            handler.handle(envelope) → ack | fail(max_attempts)
```

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Outbox model & ports — stubs | `domain/shared/outbox/`, `NoteApprovedPayload` signatures | Package layout sets a precedent for every future shared concern |
| 2. Outbox model & ports — behavior | Envelope transitions, payload snapshot | Illegal-transition guards must be total or the lifecycle silently corrupts |
| 3. `EnvelopeType` VO & in-memory adapters — stubs | `EnvelopeType`, store, appender, claimer, `uow.outbox` | Missing the snapshot set silently drops rollback coverage |
| 4. `EnvelopeType` VO & in-memory adapters — behavior | Contract suite incl. parallel claim and version cross-match | Getting the lock scope wrong hands two workers one envelope |
| 5. Capture domain — stubs | `Note` mutators, `approve()`, `close()` | — |
| 6. Capture domain — behavior | Guards, one-way approval, session close | Approval must be irreversible under every path |
| 7. Redraft & approval command — stubs | `ApproveNoteCommand`, redraft seam, DTO | — |
| 8. Redraft & approval command — behavior | In-place redraft, one-transaction approval | A partial write here leaves an approved note with no envelope |
| 9. Worker — stubs | `OutboxHandler`, `OutboxWorker`, stub handler | — |
| 10. Worker — behavior | Dispatch, retry, dead-letter, parallel safety | A leaked exception in the loop kills the task silently |
| 11. HTTP & settings — stubs | Routes, `Environment`, worker settings | — |
| 12. HTTP & settings — behavior | Status codes, prod gating of `/_outbox` | Gating on schema visibility alone would leave the route live on prod |
| 13. Composition & lifecycle | compose wiring, lifespan task, logging | Two store instances would leave the worker polling an empty queue |
| 14. TUI approval — stubs | Regenerated schema, client fn, store field | — |
| 15. TUI approval — behavior | `/approve` interception, terminal render | A loose match would send prose containing "approve" as an approval |
| 16. Acceptance scenarios | US-06/US-07 features, steps, markers | Unregistered step module never loads |

**Prerequisites:** S-04 (`capture-flow-draft-note`, archived). No dependency on S-03 or S-05.
**Estimated effort:** Large — 16 phases across four layers plus the TUI; eight of them are stub phases that add signatures only.

## Open Risks & Assumptions

- **The `hexagonal-arch-shape` ADR amendment is not paid here.** The duck session recorded that the ADR's directory convention has no shared bucket and owes an amendment once `domain/shared/` exists. This slice creates the bucket and leaves the ADR describing a layout the code no longer matches.
- **`/_outbox` reaches the TUI's generated schema.** Outside production it is a normal documented route, so a local `pnpm generate:api` writes it into `tui/src/api/generated/schema.d.ts`. The TUI never calls it, but internal queue mechanics do land in the client's type surface.
- **An envelope stranded in `processing` is never recovered** until lease/reclaim is built — see `plan.md`'s `## Migration Notes`.
- **The redraft branch assumes the model re-emits the complete draft shape each turn**, which the current deterministic adapter's chunk contract guarantees; a future LLM adapter emitting partial redrafts would need the reconciliation rewritten.
- **The stub handler proves mechanics, not a business effect.** Nothing is actually saved anywhere until `distill` exists.

## Success Criteria (Summary)

- A drafting turn followed by a change request leaves one `Note` — same id — reshaped to the latest turn's topic, tags and body, with no direct text editing anywhere in the flow.
- No envelope exists in the outbox until the approval endpoint succeeds; that call approves the note, closes the session and appends the envelope in one transaction, or does none of it.
- The worker running beside the API claims each envelope exactly once even under two concurrent workers, retries a failing handler up to `max_attempts`, and settles the envelope as `consumed` or `failed`.
