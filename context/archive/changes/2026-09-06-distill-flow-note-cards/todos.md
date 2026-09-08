---
change_id: distill-flow-note-cards
current_phase: 6
next_step:
next_command: /archive distill-flow-note-cards
updated: 2026-09-08
---

### Phase 1: Backend card-read contracts

#### Automated

- [x] 1.1 Add ListCardsForNoteQueryPort and CardListItemDTO — 48d0bbe
- [x] 1.2 Add InMemoryListCardsForNoteQueryAdapter shell — 48d0bbe
- [x] 1.3 Add GET /notes/{note_id}/cards route — 48d0bbe
- [x] 1.4 Wire the card list query in compose — 48d0bbe
- [x] 1.5 Run backend pytest and lint — 48d0bbe

#### Manual

- [x] 1.6 Start the backend and confirm the route appears in openapi.json — 48d0bbe

### Phase 2: Backend card-read behavior

#### Tests

- [x] tests generated — 1ec7311

#### Automated

- [x] 2.1 Implement live-card filter, created_at ordering and 404 — b85eded
- [x] 2.2 Add HTTP integration cases for cards, empty, discarded and unknown note — 1ec7311
- [x] 2.3 Run backend pytest — b85eded

#### Manual

- [x] 2.4 Curl the cards route for a generated note and for an unknown note id — 5e1f5d4

### Phase 3: OpenAPI regeneration and TUI card surface stubs

#### Automated

- [x] 3.1 Regenerate schema.d.ts against the running backend — a35a3f4
- [x] 3.2 Add tui/src/api/cards.ts signatures — a35a3f4
- [x] 3.3 Add tui/src/store/cards.ts store shape — a35a3f4
- [x] 3.4 Run tui build and tests — a35a3f4

#### Manual

- [x] 3.5 Confirm the regenerated schema carries the cards path and DTO — a35a3f4

### Phase 4: TUI card fetch behavior

#### Tests

- [x] tests generated — 0294329

#### Automated

- [x] 4.1 Implement listCards mapping and status-aware errors — df29c91
- [x] 4.2 Implement useCardsStore fetch, refresh and error paths — df29c91
- [x] 4.3 Add cards API and cards store test suites — df29c91
- [x] 4.4 Run tui tests and build — df29c91

### Phase 5: TUI navigation and screen stubs

#### Automated

- [x] 5.1 Extend useAppStore with activeNoteTab and selectedCardId — 2ac4ba5
- [x] 5.2 Add NoteTabStrip component — 2ac4ba5
- [x] 5.3 Add CardListScreen and CardDetailScreen shells — 2ac4ba5
- [x] 5.4 Run tui build and tests — 2ac4ba5

#### Manual

- [x] 5.5 Confirm existing note navigation is unchanged with the new state inert — 2ac4ba5

### Phase 6: TUI navigation behavior and card screens

#### Tests

- [x] tests generated — 6da0302

#### Automated

- [x] 6.1 Add tab strip and right-arrow entry to NoteDetailScreen — 739ebc3
- [x] 6.2 Implement CardListScreen fetch, selection, refresh and empty state — 739ebc3
- [x] 6.3 Implement CardDetailScreen render and left-arrow back — 739ebc3
- [x] 6.4 Route tab and card depth in app.tsx — 739ebc3
- [x] 6.5 Add card screen and navigation test suites — 739ebc3
- [x] 6.6 Run tui tests, tui build and backend pytest — 739ebc3

#### Manual

- [x] 6.7 Walk the tab and depth axes in the running TUI, including a zero-card note — 739ebc3

#### Triage

- [x] 6.8 R1-F1 Card list keeps another note's cards visible while the new note loads (proof: 17a8cd4) — ef833f5
