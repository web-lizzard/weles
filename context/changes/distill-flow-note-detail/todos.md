---
change_id: distill-flow-note-detail
current_phase: 5
next_step: 5.1
next_command: /implement distill-flow-note-detail phase 5
updated: 2026-09-07
---

### Phase 1: GetNote read model — interfaces

#### Automated

- [x] 1.1 basedpyright on exception/errors/port/DTO/adapter-skeleton files — 7759434
- [x] 1.2 pytest test_http_error_mapping.py (exhaustiveness) — 7759434

### Phase 2: GetNote read model — behavior

#### Tests

- [x] tests generated — d41bbd9

#### Automated

- [x] 2.1 pytest test_get_note_query.py — bdaf7e9

### Phase 3: `GET /notes/{note_id}` route — interfaces

#### Automated

- [x] 3.1 basedpyright on notes.py / compose.py — 0cd5c99

### Phase 4: `GET /notes/{note_id}` route — behavior

#### Tests

- [x] tests generated — 3a12ace

#### Automated

- [x] 4.1 pytest test_notes_http.py — 3b9e802

#### Manual

- [x] 4.2 curl /notes/{id} — 200 known id, 404 unknown id — 3b9e802
- [x] 4.3 pnpm generate:api — schema.d.ts gains /notes/{note_id} — 3b9e802

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
