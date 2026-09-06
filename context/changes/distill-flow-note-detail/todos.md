---
change_id: distill-flow-note-detail
current_phase: 1
next_step: 1.1
next_command: /implement distill-flow-note-detail phase 1
updated: 2026-09-06
---

### Phase 1: GetNote read model — interfaces

#### Automated

- [ ] 1.1 basedpyright on exception/errors/port/DTO/adapter-skeleton files
- [ ] 1.2 pytest test_http_error_mapping.py (exhaustiveness)

### Phase 2: GetNote read model — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 2.1 pytest test_get_note_query.py

### Phase 3: `GET /notes/{note_id}` route — interfaces

#### Automated

- [ ] 3.1 basedpyright on notes.py / compose.py

### Phase 4: `GET /notes/{note_id}` route — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 pytest test_notes_http.py

#### Manual

- [ ] 4.2 curl /notes/{id} — 200 known id, 404 unknown id
- [ ] 4.3 pnpm generate:api — schema.d.ts gains /notes/{note_id}

### Phase 5: Notes API client `getNote` — interfaces

#### Automated

- [ ] 5.1 pnpm typecheck

### Phase 6: Notes API client `getNote` — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 6.1 pnpm vitest run test/notes.test.ts

### Phase 7: Note detail navigation state — interfaces

#### Automated

- [ ] 7.1 pnpm typecheck

### Phase 8: Note detail navigation state — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 8.1 pnpm vitest run test/noteDetailStore.test.ts
- [ ] 8.2 pnpm vitest run test/appStore.test.ts

### Phase 9: `NoteDetailScreen` — interfaces

#### Automated

- [ ] 9.1 pnpm typecheck

### Phase 10: `NoteDetailScreen` — rendering

#### Tests

- [ ] tests generated

#### Automated

- [ ] 10.1 pnpm vitest run test/noteDetailScreen.test.tsx

### Phase 11: List navigation + shell wiring

#### Tests

- [ ] tests generated

#### Automated

- [ ] 11.1 pnpm vitest run test/noteListOverlay.test.tsx (extended)
- [ ] 11.2 pnpm vitest run test/app.test.tsx (extended)
