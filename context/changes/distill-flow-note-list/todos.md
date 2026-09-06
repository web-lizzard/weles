---
change_id: distill-flow-note-list
current_phase: 4
next_step: 4.1
next_command: /unit-test distill-flow-note-list phase 4
updated: 2026-09-06
---

### Phase 1: Note recency — interfaces

#### Automated

- [x] 1.1 Add `Note.updated_at` field and private `_touch` stub — `domain/distill/note.py` — ba73429
- [x] 1.2 `cd backend && uv run pytest tests/unit/distill/test_note.py` still green and `uv run basedpyright src/domain/distill/note.py` clean — ba73429

### Phase 2: Note recency — wiring

#### Tests

- [x] tests generated — dbba68e

#### Automated

- [x] 2.1 Wire `_touch` into `mint_note`, `mark_ready`, `mark_failed` — `domain/distill/note.py`
- [x] 2.2 Write the recency tests (mint sets it, mark_ready/mark_failed bump it, invalid transition doesn't) — `tests/unit/distill/test_note.py` — dbba68e
- [x] 2.3 `cd backend && uv run pytest tests/unit/distill/test_note.py` green

### Phase 3: ListNotes read model — interfaces

#### Automated

- [x] 3.1 Add `NoteListItemDTO` and `ListNotesQueryPort` — `application/distill/queries/list_notes.py`
- [x] 3.2 Add `NoteRepository.list_all()` to the port — `domain/distill/ports.py`
- [x] 3.3 Add `list_all()` stub — `adapters/out/in_memory/distill/note_repository.py`
- [x] 3.4 Add `InMemoryListNotesQuery` skeleton — `adapters/out/in_memory/distill/list_notes_query.py`
- [x] 3.5 `cd backend && uv run basedpyright src/application/distill/queries/list_notes.py src/adapters/out/in_memory/distill/list_notes_query.py` clean

### Phase 4: ListNotes read model — logic

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 Implement `list_all()` — `adapters/out/in_memory/distill/note_repository.py`
- [ ] 4.2 Implement `InMemoryListNotesQuery.list_notes()` (live-card filter, status passthrough, recency `max()` ordering) — `adapters/out/in_memory/distill/list_notes_query.py`
- [ ] 4.3 Add `list_all()` contract-test case — `tests/unit/distill/contracts/test_note_repository_contract.py`
- [ ] 4.4 Write the ListNotes query tests (three-way status, discard filter, ordering, empty list) — `tests/unit/distill/test_list_notes_query.py`
- [ ] 4.5 `cd backend && uv run pytest tests/unit/distill/contracts/test_note_repository_contract.py tests/unit/distill -k list_notes` green

### Phase 5: `GET /notes` route — interfaces

#### Automated

- [ ] 5.1 Add `router` and unimplemented `list_notes` route — `adapters/http/notes.py`
- [ ] 5.2 Add `_list_notes_query` singleton and `get_list_notes_query()` — `adapters/compose.py`
- [ ] 5.3 `cd backend && uv run basedpyright src/adapters/http/notes.py src/adapters/compose.py` clean

### Phase 6: `GET /notes` route — wiring

#### Tests

- [ ] tests generated

#### Automated

- [ ] 6.1 Implement the route body (`return await query.list_notes()`) — `adapters/http/notes.py`
- [ ] 6.2 Register `notes_router` unconditionally — `main.py`
- [ ] 6.3 Add `notes_client` fixture — `tests/integration/conftest.py`
- [ ] 6.4 Write the `GET /notes` integration test — `tests/integration/test_notes_http.py`
- [ ] 6.5 `cd backend && uv run pytest tests/integration/test_notes_http.py` green

#### Manual

- [ ] 6.6 `cd backend && uv run fastapi dev src/main.py`, then `curl localhost:8000/notes` and confirm the JSON shape
- [ ] 6.7 `cd tui && pnpm generate:api` (backend running) and confirm `schema.d.ts` gains a `/notes` path

### Phase 7: Notes API client — interfaces

#### Automated

- [ ] 7.1 Add `NoteListItem` type and unimplemented `listNotes()` — `tui/src/api/notes.ts`
- [ ] 7.2 `cd tui && pnpm typecheck` clean

### Phase 8: Notes API client — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 8.1 Implement `listNotes()` request + snake_case→camelCase mapping — `tui/src/api/notes.ts`
- [ ] 8.2 Write the notes-client tests (mapping, thrown error) — `tui/test/notes.test.ts`
- [ ] 8.3 `cd tui && pnpm vitest run test/notes.test.ts` green

### Phase 9: Notes data store — interfaces

#### Automated

- [ ] 9.1 Add `useNotesStore` skeleton — `tui/src/store/notes.ts`
- [ ] 9.2 Add `useNotesPolling` hook skeleton — `tui/src/hooks/useNotesPolling.ts`
- [ ] 9.3 `cd tui && pnpm typecheck` clean

### Phase 10: Notes data store — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 10.1 Implement `fetchNotes`/`startPolling`/`stopPolling` — `tui/src/store/notes.ts`
- [ ] 10.2 Implement `useNotesPolling`'s mount/unmount lifecycle — `tui/src/hooks/useNotesPolling.ts`
- [ ] 10.3 Write the notes-store tests (fake timers: immediate + interval fetch, stop, error-then-recover) — `tui/test/notesStore.test.ts`
- [ ] 10.4 `cd tui && pnpm vitest run test/notesStore.test.ts` green

### Phase 11: Overlay shell + dispatch — interfaces

#### Automated

- [ ] 11.1 Add `isNotesOverlayOpen`/`openNotes`/`closeNotes` to `useAppStore` — `tui/src/store/index.ts`
- [ ] 11.2 Add `NOTES_COMMAND` constant — `tui/src/screens/CaptureScreen.tsx`
- [ ] 11.3 Import `useInput`, read overlay state, unimplemented handler — `tui/src/app.tsx`
- [ ] 11.4 `cd tui && pnpm typecheck` clean

### Phase 12: Overlay shell + dispatch — wiring

#### Tests

- [ ] tests generated

#### Automated

- [ ] 12.1 Implement `openNotes`/`closeNotes` — `tui/src/store/index.ts`
- [ ] 12.2 Wire the `/notes` dispatch branch and `isNotesCommand` highlight — `tui/src/screens/CaptureScreen.tsx`
- [ ] 12.3 Render `NoteListOverlay` conditionally and wire the ESC handler — `tui/src/app.tsx`
- [ ] 12.4 Extend the app tests (open via `/notes`, close via ESC, capture-state-unchanged assertion) — `tui/test/app.test.tsx`
- [ ] 12.5 `cd tui && pnpm vitest run test/app.test.tsx` green

### Phase 13: `NoteListOverlay` — interfaces

#### Automated

- [ ] 13.1 Add `NoteListOverlay` skeleton calling `useNotesPolling` — `tui/src/screens/NoteListOverlay.tsx`
- [ ] 13.2 Add `statusBadge` helper skeleton — `tui/src/screens/NoteListOverlay.tsx`
- [ ] 13.3 `cd tui && pnpm typecheck` clean

### Phase 14: `NoteListOverlay` — rendering

#### Tests

- [ ] tests generated

#### Automated

- [ ] 14.1 Implement `statusBadge` (three-way mapping + elapsed age) — `tui/src/screens/NoteListOverlay.tsx`
- [ ] 14.2 Implement row rendering + inline error + loading state — `tui/src/screens/NoteListOverlay.tsx`
- [ ] 14.3 Write the overlay rendering tests — `tui/test/noteListOverlay.test.tsx`
- [ ] 14.4 `cd tui && pnpm vitest run test/noteListOverlay.test.tsx` green
