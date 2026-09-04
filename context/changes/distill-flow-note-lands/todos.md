---
change_id: distill-flow-note-lands
current_phase: 6
next_step: 6.1
next_command: /unit-test distill-flow-note-lands phase 6
updated: 2026-09-04
---

### Phase 1: Note domain model — stubs

#### Automated

- [x] 1.1 Create the `domain/distill/` package marker — 7672baa
- [x] 1.2 Add `NoteId`, `SessionId`, `TopicSnapshot`, `TagSnapshot`, `NoteContent` (fields only), `DistillationStatus` — `domain/distill/value_objects.py` — 7672baa
- [x] 1.3 Add `DistillEmptyNoteContentError`, `DistillNoteContentTooLongError` — `domain/distill/exceptions.py` (renamed from the plan's `EmptyNoteContentError`/`NoteContentTooLongError`: those names collide on `CoreException.code()` with capture's identically-named exceptions in `domain/capture/exceptions.py:44,48`, which `tests/unit/test_http_error_mapping.py:33-35` forbids — user chose the rename option over pinning an explicit `_code` override) — 7672baa
- [x] 1.4 Add `Note` (fields) and `mint_note` with an unimplemented signature — `domain/distill/note.py` — 7672baa
- [x] 1.5 `cd backend && uv run ruff check src`, `uv run basedpyright` clean and every new symbol importable — 7672baa

### Phase 2: Note domain model — behavior

#### Tests

- [x] tests generated — 4db1c7c

#### Automated

- [x] 2.1 Implement `NoteContent`'s strip + non-empty + bound validation — `domain/distill/value_objects.py` — 97e1079
- [x] 2.2 Implement `mint_note`'s field mapping and `generating`/`created_at` stamping — `domain/distill/note.py` — 97e1079
- [x] 2.3 Write the value-object and `mint_note` tests — `tests/unit/distill/test_value_objects.py`, `tests/unit/distill/test_note.py` — 4db1c7c
- [x] 2.4 `cd backend && uv run pytest` green (required adding `distill_empty_note_content`/`distill_note_content_too_long` to `adapters/http/errors.py`'s `EXCEPTION_STATUS_MAP` — unplanned, resolved via Adapt-and-continue: the repo-wide exhaustiveness test requires every `CoreException` subclass mapped regardless of HTTP reachability) — 97e1079

### Phase 3: NoteRepository — stubs

#### Automated

- [x] 3.1 Add the `NoteRepository` protocol — `domain/distill/ports.py` — e50923e
- [x] 3.2 Create the `adapters/out/in_memory/distill/` package marker — e50923e
- [x] 3.3 Add `InMemoryNoteRepository` with unimplemented `add`/`get`/`snapshot`/`restore` — `adapters/out/in_memory/distill/note_repository.py` — e50923e
- [x] 3.4 `cd backend && uv run ruff check src`, `uv run basedpyright` clean — e50923e

### Phase 4: NoteRepository — behavior

#### Tests

- [x] tests generated — 1cf5245

#### Automated

- [x] 4.1 Implement `InMemoryNoteRepository`'s `add`/`get`/`snapshot`/`restore` over a dict keyed by note id — `adapters/out/in_memory/distill/note_repository.py` — 66d1e8f
- [x] 4.2 Write the port contract suite — `tests/unit/distill/contracts/test_note_repository_contract.py` — 1cf5245
- [x] 4.3 `cd backend && uv run pytest` green — 66d1e8f

### Phase 5: Application layer and outbound envelope — stubs

#### Automated

- [x] 5.1 Add the `UnitOfWork` protocol (`notes` + `outbox` only) — `application/distill/ports.py` — 0a2dded
- [x] 5.2 Implement `InMemoryUnitOfWork` (snapshot/restore/commit, no independent test) — `adapters/out/in_memory/distill/unit_of_work.py` — 0a2dded
- [x] 5.3 Implement `NOTE_SAVED` and `NoteSavedPayload` with `to_envelope()` (no independent test) — `domain/distill/outbox.py` — 0a2dded
- [x] 5.4 Add `SaveNoteCommand` with an unimplemented `handle()` taking a `UnitOfWork` factory — `application/distill/commands/save_note.py` — 0a2dded
- [x] 5.5 `cd backend && uv run ruff check src`, `uv run basedpyright` clean — 0a2dded

### Phase 6: SaveNoteCommand — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 6.1 Implement `SaveNoteCommand.handle()`: idempotency check, `mint_note`, persist, enqueue `note_saved`, commit, no-op log on redelivery — `application/distill/commands/save_note.py`
- [ ] 6.2 Write the command tests incl. the redelivery no-op case — `tests/unit/distill/test_save_note_command.py`
- [ ] 6.3 `cd backend && uv run pytest` green

### Phase 7: Handler adapter — stubs

#### Automated

- [ ] 7.1 Add `SaveNoteHandler` with an unimplemented `handle()`, alongside the existing `LoggingNoteSaveHandler` — `adapters/out/worker/handlers/note_save.py`
- [ ] 7.2 `cd backend && uv run ruff check src`, `uv run basedpyright` clean

### Phase 8: Handler adapter — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 8.1 Implement `SaveNoteHandler.handle()`: validate via `NoteApprovedPayload`, unpack to distill VOs, dispatch to `SaveNoteCommand` — `adapters/out/worker/handlers/note_save.py`
- [ ] 8.2 Implement the malformed-payload path: catch `ValidationError`, log, return without raising — `adapters/out/worker/handlers/note_save.py`
- [ ] 8.3 Write the handler tests incl. the malformed-payload case — `tests/unit/distill/test_save_note_handler.py`
- [ ] 8.4 `cd backend && uv run pytest` green

### Phase 9: Composition

#### Automated

- [ ] 9.1 Wire distill's repository, `UnitOfWork` factory, command and handler, sharing capture's outbox store instances — `adapters/compose.py`
- [ ] 9.2 Register `SaveNoteHandler` in the `OutboxWorker`'s handler list in place of `LoggingNoteSaveHandler` — `adapters/compose.py`
- [ ] 9.3 Delete `LoggingNoteSaveHandler` and its now-unused imports — `adapters/out/worker/handlers/note_save.py`
- [ ] 9.4 `cd backend && uv run pytest` and `uv run ruff check src` green

#### Manual

- [ ] 9.5 Approve a note through the existing flow and confirm via `/_outbox` that `note_approved` reaches `consumed` and a new `note_saved` envelope appears
