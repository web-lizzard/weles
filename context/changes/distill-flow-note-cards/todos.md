---
change_id: distill-flow-note-cards
current_phase: 1
next_step: 1.1
next_command: /implement distill-flow-note-cards phase 1
updated: 2026-09-08
---

### Phase 1: Backend card-read contracts

#### Automated

- [ ] 1.1 Add ListCardsForNoteQueryPort and CardListItemDTO
- [ ] 1.2 Add InMemoryListCardsForNoteQueryAdapter shell
- [ ] 1.3 Add GET /notes/{note_id}/cards route
- [ ] 1.4 Wire the card list query in compose
- [ ] 1.5 Run backend pytest and lint

#### Manual

- [ ] 1.6 Start the backend and confirm the route appears in openapi.json

### Phase 2: Backend card-read behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 2.1 Implement live-card filter, created_at ordering and 404
- [ ] 2.2 Add HTTP integration cases for cards, empty, discarded and unknown note
- [ ] 2.3 Run backend pytest

#### Manual

- [ ] 2.4 Curl the cards route for a generated note and for an unknown note id

### Phase 3: OpenAPI regeneration and TUI card surface stubs

#### Automated

- [ ] 3.1 Regenerate schema.d.ts against the running backend
- [ ] 3.2 Add tui/src/api/cards.ts signatures
- [ ] 3.3 Add tui/src/store/cards.ts store shape
- [ ] 3.4 Run tui build and tests

#### Manual

- [ ] 3.5 Confirm the regenerated schema carries the cards path and DTO

### Phase 4: TUI card fetch behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 Implement listCards mapping and status-aware errors
- [ ] 4.2 Implement useCardsStore fetch, refresh and error paths
- [ ] 4.3 Add cards API and cards store test suites
- [ ] 4.4 Run tui tests and build

### Phase 5: TUI navigation and screen stubs

#### Automated

- [ ] 5.1 Extend useAppStore with activeNoteTab and selectedCardId
- [ ] 5.2 Add NoteTabStrip component
- [ ] 5.3 Add CardListScreen and CardDetailScreen shells
- [ ] 5.4 Run tui build and tests

#### Manual

- [ ] 5.5 Confirm existing note navigation is unchanged with the new state inert

### Phase 6: TUI navigation behavior and card screens

#### Tests

- [ ] tests generated

#### Automated

- [ ] 6.1 Add tab strip and right-arrow entry to NoteDetailScreen
- [ ] 6.2 Implement CardListScreen fetch, selection, refresh and empty state
- [ ] 6.3 Implement CardDetailScreen render and left-arrow back
- [ ] 6.4 Route tab and card depth in app.tsx
- [ ] 6.5 Add card screen and navigation test suites
- [ ] 6.6 Run tui tests, tui build and backend pytest

#### Manual

- [ ] 6.7 Walk the tab and depth axes in the running TUI, including a zero-card note
