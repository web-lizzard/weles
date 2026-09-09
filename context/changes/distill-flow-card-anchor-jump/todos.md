---
change_id: distill-flow-card-anchor-jump
current_phase: 7
next_step: 7.6
next_command: /implement distill-flow-card-anchor-jump phase 7
updated: 2026-09-09
---

### Phase 1: Domain anchor-location contracts

#### Automated

- [x] 1.1 Add NoteFormat protocol, NormalizedText and MarkdownNoteFormat stubs — 9cf0cfe
- [x] 1.2 Add NoteBlock, AnchorPrecision, AnchorLocation and NoteDocument stubs — 9cf0cfe
- [x] 1.3 Run backend pytest, ruff and basedpyright — 9cf0cfe

### Phase 2: Domain anchor-location behavior

#### Tests

- [x] tests generated — a5c8ebb

#### Automated

- [x] 2.1 Implement MarkdownNoteFormat blocks and normalize with the offset map — fa95fd8
- [x] 2.2 Implement NoteDocument.of and locate with exact and block precision — fa95fd8
- [x] 2.3 Add note format and note document unit suites — fa95fd8
- [x] 2.4 Run backend pytest, ruff and basedpyright — fa95fd8

#### Manual

- [x] 2.5 Resolve a sample anchor through a python one-liner — fa95fd8

#### Triage

- [x] 2.6 R1-F1 Leading emphasis at block start marks the whole paragraph (proof: 99a75f0) — a1b6a1d
- [x] 2.7 R2-F1 Multi-character and numbered leading markers are not stripped — 11ed503
- [x] 2.8 R2-F2 Block split strips indentation not just newlines — 11ed503
- [x] 2.9 R2-F3 Normalize does not pin trimming of leading and trailing whitespace — 11ed503
- [x] 2.10 R2-F4 Locate takes the last in-block match — 11ed503
- [x] 2.11 R2-F5 Exact end bound can extend one raw character past the quote — 11ed503

### Phase 3: Generation on the domain locator

#### Automated

- [x] 3.1 Delete the NoteDocumentParser port and its markdown adapter — 00073db
- [x] 3.2 Move GenerateCards onto NoteDocument.locate — 00073db
- [x] 3.3 Drop the parser from compose — 00073db
- [x] 3.4 Migrate the parser-shaped unit, integration and bdd test surfaces — 00073db
- [x] 3.5 Run backend pytest, the bdd suite, ruff and basedpyright — 00073db

#### Manual

- [x] 3.6 Approve a note end to end and confirm cards are still grounded — 00073db

### Phase 4: Read-model anchor contracts

#### Automated

- [x] 4.1 Add NoteBlockDTO and blocks to NoteDetailDTO — 9cc4aa7
- [x] 4.2 Add AnchorLocationDTO and anchor_location to CardListItemDTO — 9cc4aa7
- [x] 4.3 Wire both query adapters to empty values — 9cc4aa7
- [x] 4.4 Run backend pytest, ruff and basedpyright — 9cc4aa7

#### Manual

- [x] 4.5 Confirm both new shapes appear in openapi.json — 9cc4aa7

### Phase 5: Read-model behavior and US-07 acceptance

#### Tests

- [x] tests generated — 955882b

#### Automated

- [x] 5.1 Fill blocks from NoteDocument in the note detail adapter — d2f23b3
- [x] 5.2 Resolve anchor_location per live card in the cards adapter — d2f23b3
- [x] 5.3 Add HTTP integration cases for blocks and the three location outcomes — d2f23b3
- [x] 5.4 Add the US-07 feature, step module and loader entry — d2f23b3
- [x] 5.5 Run backend pytest, the AC-13 scenarios, ruff and basedpyright — d2f23b3

#### Manual

- [x] 5.6 Curl both routes for a generated note and inspect a location — d2f23b3

### Phase 6: TUI anchor surface stubs

#### Automated

- [x] 6.1 Regenerate schema.d.ts against the running backend — 19d270d
- [x] 6.2 Add NoteBlock and blocks to the notes API module — 19d270d
- [x] 6.3 Add AnchorLocation and anchorLocation to the cards API module — 19d270d
- [x] 6.4 Add highlightedAnchor and jumpToAnchor to useAppStore — 19d270d
- [x] 6.5 Run tui typecheck, lint, build and tests — 19d270d

#### Manual

- [x] 6.6 Confirm the regenerated schema carries anchor_location — 19d270d

### Phase 7: Jump gesture and anchored highlight

#### Tests

- [x] tests generated — cb340ba

#### Automated

- [x] 7.1 Implement jumpToAnchor and the four clearing transitions — c24e9f4
- [x] 7.2 Add the Enter jump and hint line to CardDetailScreen — c24e9f4
- [x] 7.3 Render note blocks with the anchored viewport, marked span and notice — c24e9f4
- [x] 7.4 Add card detail, note detail and store test suites — c24e9f4
- [x] 7.5 Run tui tests, typecheck, lint, build and backend pytest — c24e9f4

#### Manual

- [ ] 7.6 Walk the jump in the running TUI, including a heading-anchored card
