---
change_id: capture-flow-review-approve-outbox
current_phase: 19
next_step: 19.5
next_command: /implement capture-flow-review-approve-outbox phase 19
updated: 2026-09-02
---

### Phase 1: Outbox model and ports — stubs

#### Automated

- [x] 1.1 Create the `domain/shared/` and `domain/shared/outbox/` package markers — 0fb5563
- [x] 1.2 Add `EnvelopeStatus`, `EnvelopeId`, `OutboxEnvelope` with unimplemented transitions — `domain/shared/outbox/model.py` — 0fb5563
- [x] 1.3 Add `EnvelopeNotPendingError`, `EnvelopeNotProcessingError` — `domain/shared/outbox/exceptions.py` — 0fb5563
- [x] 1.4 Add the `OutboxAppender` and `OutboxClaimer` protocols — `domain/shared/outbox/ports.py` — 0fb5563
- [x] 1.5 Add `NOTE_APPROVED`, `VocabularySnapshot`, `NoteApprovedPayload` with unimplemented `of()`/`to_envelope()` — `domain/capture/outbox.py` — 0fb5563
- [x] 1.6 `cd backend && uv run ruff check src`, `uv run basedpyright` clean and every new symbol importable — 0fb5563

### Phase 2: Outbox model and ports — behavior

#### Tests

- [x] tests generated — 371d1f5

#### Automated

- [x] 2.1 Implement `OutboxEnvelope.pending()` with `PENDING`, zero attempts and null claim fields — 53509c2
- [x] 2.2 Implement `claim()`, `consume()` and `fail(max_attempts)` with their status guards and the retry cut-off — 53509c2
- [x] 2.3 Implement `NoteApprovedPayload.of()` snapshotting topic and tag labels, and `to_envelope()` — 53509c2
- [x] 2.4 Add `envelope_not_pending` and `envelope_not_processing` to `EXCEPTION_STATUS_MAP` — `adapters/http/errors.py` — 53509c2
- [x] 2.5 `cd backend && uv run pytest` green — 53509c2

### Phase 3: Envelope type VO and in-memory outbox adapters — stubs

#### Automated

- [x] 3.1 Add the `EnvelopeType` VO (`name`, `version=1`, `__str__` as `name@version`) — `domain/shared/outbox/model.py` — 7a9445b
- [x] 3.2 Change `OutboxEnvelope.type` and `pending()`'s `type` param from `str` to `EnvelopeType` — `domain/shared/outbox/model.py` — 7a9445b
- [x] 3.3 Migrate `NOTE_APPROVED` to an `EnvelopeType` instance — `domain/capture/outbox.py` — 7a9445b
- [x] 3.4 Create the `adapters/out/in_memory/shared/` and `.../shared/outbox/` package markers — 7a9445b
- [x] 3.5 Add `InMemoryOutboxStore` with `snapshot`/`restore`/`put`/`select_pending`/`lock`/`all`, `select_pending` typed on `EnvelopeType` — `.../shared/outbox/store.py` — 7a9445b
- [x] 3.6 Add `InMemoryOutboxAppender` and `InMemoryOutboxClaimer` with unimplemented bodies, `claim` typed on `EnvelopeType` — `.../appender.py`, `.../claimer.py` — 7a9445b
- [x] 3.7 Add `outbox: OutboxAppender` to the `UnitOfWork` protocol — `application/capture/ports.py` — 7a9445b
- [x] 3.8 Widen `InMemoryUnitOfWork`'s constructor and snapshot set with the outbox store — `adapters/out/in_memory/capture/unit_of_work.py` — 7a9445b
- [x] 3.9 `cd backend && uv run ruff check src`, `uv run basedpyright` clean — 7a9445b

### Phase 4: Envelope type VO and in-memory outbox adapters — behavior

#### Tests

- [x] tests generated — 35a8f55

#### Automated

- [x] 4.1 Implement `InMemoryOutboxAppender.append()` and the store's put/select — a55719a
- [x] 4.2 Implement `InMemoryOutboxClaimer.claim()` holding the store lock across select-and-mutate, matching `EnvelopeType` by `name` and `version` — a55719a
- [x] 4.3 Implement `ack()` and `fail()` persisting the caller's already-applied transition — a55719a
- [x] 4.4 Write the port contract suite incl. the `asyncio.gather` disjoint-claim case and the version cross-match case — `tests/unit/shared/test_outbox_contract.py` — a55719a
- [x] 4.5 Extend the UnitOfWork tests to cover outbox rollback — `tests/unit/capture/test_unit_of_work.py` — a55719a
- [x] 4.6 `cd backend && uv run pytest` green — a55719a

### Phase 5: Capture domain approval and mutators — stubs

#### Automated

- [x] 5.1 Add `update_content`, `change_topic`, `add_tag`, `remove_tag`, `approve` signatures to `Note` — `domain/capture/note.py` — 52c4d84
- [x] 5.2 Add `approve(note)` and `close()` signatures to `CaptureSession` — `domain/capture/capture_session.py` — 52c4d84
- [x] 5.3 Add `NoteNotDraftError`, `NoteSessionMismatchError`, `SessionNoteMissingError`, `NoteNotFoundError`, `TagNotOnNoteError` — `domain/capture/exceptions.py` — 52c4d84
- [x] 5.4 `cd backend && uv run ruff check src`, `uv run basedpyright` clean — 52c4d84

### Phase 6: Capture domain approval and mutators — behavior

#### Tests

- [x] tests generated — fed160c

#### Automated

- [x] 6.1 Implement the four `Note` mutators under the draft-only guard, incl. duplicate-add and missing-tag handling — af7d117
- [x] 6.2 Implement `Note.approve()` with the session-match sanity check and the one-way status transition — af7d117
- [x] 6.3 Implement `CaptureSession.approve()` and `close()` so approval always closes the session — af7d117
- [x] 6.4 Add the five new codes to `EXCEPTION_STATUS_MAP` — `adapters/http/errors.py` — af7d117
- [x] 6.5 `cd backend && uv run pytest` green — af7d117

### Phase 7: Redraft and approval command — stubs

#### Automated

- [x] 7.1 Add `ApproveNoteCommand` with an unimplemented `handle()` — `application/capture/commands/approve_note.py` — 6ef26ee
- [x] 7.2 Add `ApproveNoteResponseDTO` — `application/capture/dto.py` — 6ef26ee
- [x] 7.3 Add the `_apply_redraft` seam and the `session.note_id` branch point — `application/capture/commands/send_message.py` — 6ef26ee
- [x] 7.4 `cd backend && uv run ruff check src`, `uv run basedpyright` clean — 6ef26ee

### Phase 8: Redraft and approval command — behavior

#### Tests

- [x] tests generated — 4e9352c

#### Automated

- [x] 8.1 Implement the redraft branch: load the note, `change_topic`, reconcile tags, `update_content`, re-save — 41725d6
- [x] 8.2 Keep `draft_done` carrying the original `note_id` across every redraft turn — 41725d6
- [x] 8.3 Implement `ApproveNoteCommand.handle()`: approve, save both aggregates, load topic and tags, append the envelope, commit — 41725d6
- [x] 8.4 Write the command unit tests, incl. the rollback case leaving zero envelopes — 41725d6
- [x] 8.5 `cd backend && uv run pytest` green — 41725d6

### Phase 9: Outbox worker — stubs

#### Automated

- [x] 9.1 Create the `application/shared/` and `application/shared/outbox/` package markers — 8c289bc
- [x] 9.2 Add the `OutboxHandler` protocol — `application/shared/outbox/ports.py` — 8c289bc
- [x] 9.3 Add `OutboxWorker` with unimplemented `run_once()`/`run_forever()` — `adapters/out/worker/outbox_worker.py` — 8c289bc
- [x] 9.4 Add `LoggingNoteSaveHandler` bound to `NOTE_APPROVED` — `adapters/out/worker/handlers/note_save.py` — 8c289bc
- [x] 9.5 `cd backend && uv run ruff check src`, `uv run basedpyright` clean — 8c289bc

### Phase 10: Outbox worker — behavior

#### Tests

- [x] tests generated — 39190b3

#### Automated

- [x] 10.1 Implement `run_once()`: claim per handler, handle, consume and ack — 4af9a46
- [x] 10.2 Implement the failure path: `fail(max_attempts)`, persist, log, continue to the next envelope — 4af9a46
- [x] 10.3 Implement `run_forever()` swallowing every exception except `CancelledError` — 4af9a46
- [x] 10.4 Implement `LoggingNoteSaveHandler.handle()` validating the payload back into `NoteApprovedPayload` — 4af9a46
- [x] 10.5 Write the worker tests incl. two concurrent workers over one claimer — `tests/unit/shared/test_outbox_worker.py` — 39190b3
- [x] 10.6 `cd backend && uv run pytest` green — 4af9a46

### Phase 11: HTTP surface and settings — stubs

#### Automated

- [x] 11.1 Add `Environment` and the four outbox settings fields — `config/settings.py` — 9cf6099
- [x] 11.2 Add the `POST /capture-sessions/{session_id}/approval` route signature — `adapters/http/capture.py` — 9cf6099
- [x] 11.3 Add `OutboxEnvelopeDTO` and the `OutboxEnvelopeQueryPort` — `application/shared/outbox/{dto.py,queries/envelopes.py}` — 9cf6099
- [x] 11.4 Add `InMemoryOutboxEnvelopeQueryAdapter` — `adapters/out/in_memory/shared/outbox/envelope_query.py` — 9cf6099
- [x] 11.5 Add the `GET /_outbox` router — `adapters/http/outbox.py` — 9cf6099
- [x] 11.6 `cd backend && uv run ruff check src`, `uv run basedpyright` clean — 9cf6099

### Phase 12: HTTP surface and settings — behavior

#### Tests

- [x] tests generated — 1f236d5

#### Automated

- [x] 12.1 Wire the approval route to `ApproveNoteCommand` so all four outcomes surface their codes — b2dfeb9
- [x] 12.2 Implement the envelope query adapter over the store — b2dfeb9
- [x] 12.3 Include the `/_outbox` router only when `environment_name != prod` — `main.py` — b2dfeb9
- [x] 12.4 Write the integration tests for approval, `/_outbox` content, and the production 404 plus OpenAPI absence — b2dfeb9
- [x] 12.5 `cd backend && uv run pytest` green — b2dfeb9

### Phase 13: Composition and worker lifecycle

#### Automated

- [x] 13.1 Wire one `InMemoryOutboxStore` behind the appender, claimer and query in `adapters/compose.py` — 32abd44
- [x] 13.2 Add `get_approve_note_command()`, `get_outbox_envelope_query()` and `get_outbox_worker()` — 32abd44
- [x] 13.3 Add the lifespan handler starting and cancelling the `run_forever` task — `main.py` — 32abd44
- [x] 13.4 Add INFO/WARNING/ERROR logging in the worker and the stub handler — 32abd44
- [x] 13.5 `cd backend && uv run pytest` and `uv run ruff check src` green — 32abd44

#### Manual

- [x] 13.6 Start `uv run fastapi dev src/main.py` and confirm the idle worker logs no errors
- [x] 13.7 `curl http://localhost:8000/_outbox` returns `[]`

### Phase 14: TUI approval — stubs

#### Automated

- [x] 14.1 Regenerate `src/api/generated/schema.d.ts` with `pnpm generate:api` against the running backend — 1adebc0
- [x] 14.2 Add `approveNote(sessionId)` — `tui/src/api/stream.ts` — 1adebc0
- [x] 14.3 Add `approved` state and the `approveDraft` action signature — `tui/src/store/chat.ts` — 1adebc0
- [x] 14.4 `cd tui && pnpm typecheck && pnpm lint` clean — 1adebc0

### Phase 15: TUI approval — behavior

#### Tests

- [x] tests generated — b4f5757

#### Automated

- [x] 15.1 Intercept the exact literal `/approve` in `handleSubmit` — `tui/src/screens/CaptureScreen.tsx` — a9e0d1d
- [x] 15.2 Implement `approveDraft()` with the local no-draft guard and the error path leaving `approved` false — a9e0d1d
- [x] 15.3 Replace the draft panel with the confirmation and unfocus the input when `approved` — incl. the row-budget heuristic — a9e0d1d
- [x] 15.4 Write the store and screen tests, incl. prose containing "approve" going out as a normal turn — a9e0d1d
- [x] 15.5 `cd tui && pnpm test && pnpm typecheck && pnpm lint` green — a9e0d1d

#### Manual

- [x] 15.6 Converse, wrap up, request a change and confirm the panel updates while `note_id` stays the same — 5154da0
- [x] 15.7 Type `/approve` and confirm the confirmation renders, input locks, and the worker log shows claim and handle — 5154da0

### Phase 16: Acceptance scenarios for US-06 and US-07

#### Automated

- [x] 16.1 Register the `AC-12`–`AC-15` markers — `backend/pyproject.toml` — c273574
- [x] 16.2 Write `US-06-reshape-draft.feature` covering AC-12 and AC-13 — `tests/features/capture-flow/` — c273574
- [x] 16.3 Write `US-07-approve-to-outbox.feature` covering AC-14 and AC-15 — `tests/features/capture-flow/` — c273574
- [x] 16.4 Write the step module and register it in `pytest_plugins` — `tests/bdd/steps/approve_outbox.py`, `tests/bdd/test_features.py` — c273574
- [x] 16.5 `cd backend && uv run pytest tests/bdd -v` green and `-m "capture-flow and AC-14"` selects a scenario — c273574

#### Manual

- [x] 16.6 `cd backend && uv run pytest tests/bdd --collect-only` lists the new scenarios with no undefined steps — c273574

### Phase 17: Note vocabulary composition — stubs

#### Automated

- [x] 17.1 Add `NoteVocabulary` and `NoteVocabularyRepository` — `domain/capture/ports.py` — 0c8400e
- [x] 17.2 Add `NoteVocabularyIncompleteError` — `domain/capture/exceptions.py` — 0c8400e
- [x] 17.3 Add `InMemoryNoteVocabularyRepository` with unimplemented `resolve()` — `adapters/out/in_memory/capture/note_vocabulary_repository.py` — 0c8400e
- [x] 17.4 Add `note_vocabulary: NoteVocabularyRepository` to `UnitOfWork` — `application/capture/ports.py` — 0c8400e
- [x] 17.5 Widen `InMemoryUnitOfWork`'s constructor with `note_vocabulary` — `adapters/out/in_memory/capture/unit_of_work.py` — 0c8400e
- [x] 17.6 Wire `_note_vocabulary` into `compose.py`'s `_unit_of_work()` — 0c8400e
- [x] 17.7 `cd backend && uv run ruff check src`, `uv run basedpyright` clean — 0c8400e

### Phase 18: Note vocabulary composition — behavior

#### Tests

- [x] tests generated — a78b521

#### Automated

- [x] 18.1 Implement `InMemoryNoteVocabularyRepository.resolve()` incl. `NoteVocabularyIncompleteError` guards — cdc2a02
- [x] 18.2 Add `note_vocabulary_incomplete` to `EXCEPTION_STATUS_MAP` — `adapters/http/errors.py` — cdc2a02
- [x] 18.3 Replace `ApproveNoteCommand`'s inline topic/tag loop with `uow.note_vocabulary.resolve(note)` — cdc2a02
- [x] 18.4 Replace `_apply_redraft`'s per-dropped-tag loop with one `resolve()` call and an in-memory diff — cdc2a02
- [x] 18.5 Write the port contract suite — `tests/unit/capture/contracts/test_note_vocabulary_repository_contract.py` — a78b521
- [x] 18.6 Widen `_make_approve_stack()`/`_make_command_stack()` with the new collaborator — 0c8400e
- [x] 18.7 `cd backend && uv run pytest` green — cdc2a02

### Phase 19: TUI post-approve — next capture session

#### Tests

- [x] tests generated — 63ab186

#### Automated

- [x] 19.1 On approve success: record thick-rule receipt, clear capture fields, start a new session via `startCaptureSession` — `tui/src/store/chat.ts`
- [x] 19.2 Render full-width `═` rule + `✓ Approved — queued for saving`; keep `TextInput` focused after approve — `tui/src/screens/CaptureScreen.tsx`
- [x] 19.3 Rewrite store/screen tests for auto-reset, new `sessionId`, and focused input — `tui/test/chat.test.ts`, `tui/test/captureScreen.test.tsx`
- [x] 19.4 `cd tui && pnpm test && pnpm typecheck && pnpm lint` green

#### Manual

- [ ] 19.5 Approve a draft and confirm the TUI stays open with the thick-rule receipt and accepts input for a new topic on a new session
