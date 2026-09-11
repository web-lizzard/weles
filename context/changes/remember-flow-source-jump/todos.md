---
change_id: remember-flow-source-jump
current_phase: 6
next_step: 6.1
next_command: /implement remember-flow-source-jump phase 6
updated: 2026-09-11
---

### Phase 1: Event payload union

#### Automated

- [x] 1.1 Remember unit suite passes unchanged — 323a8e4
- [x] 1.2 basedpyright reports no new errors in domain/remember — 323a8e4
- [x] 1.3 ruff check passes on src — 323a8e4

### Phase 2: Migrate the review log to payloads

#### Automated

- [x] 2.1 test_sitting.py passes with the pinned draw-seed values unchanged — 35861b3
- [x] 2.2 Remember property suite passes — 35861b3
- [x] 2.3 Full backend suite passes — 35861b3
- [x] 2.4 basedpyright reports no new errors across src — 35861b3

#### Triage

- [x] 2.5 R1-F7 partition_due must receive scheduler stamp from GradeCardCommand.handle — d82b28e
- [x] 2.6 R1-F8 GradeAppliedDTO omits outstanding_count when sitting completes — d82b28e
- [x] 2.7 R1-F9 GradeAppliedDTO omits due when sitting completes — d82b28e
- [x] 2.8 R1-F10 GradeAppliedDTO omits next_front when another card remains — d82b28e
- [x] 2.9 R1-F11 GradeAppliedDTO omits outstanding_count when sitting continues — d82b28e

### Phase 3: Non-accounting payloads stop counting

#### Tests

- [x] tests generated — bb8fb78

#### Automated

- [x] 3.1 test_sitting.py passes with existing tests unmodified — f8f56fc
- [x] 3.2 Remember property suite passes — f8f56fc
- [x] 3.3 Remember unit and integration suites pass — f8f56fc

### Phase 4: Source port, DTO, route and wiring

#### Automated

- [x] 4.1 basedpyright reports no new errors across src — 32f600b
- [x] 4.2 ruff check passes on src — 32f600b
- [x] 4.3 test_remember_routes.py passes with reveal calls switched to POST — 32f600b

### Phase 5: Revealing the back records the fact

#### Tests

- [x] tests generated — f7e2d0a

#### Automated

- [x] 5.1 test_reveal_back_command.py passes — 025a887
- [x] 5.2 Remember unit and integration suites pass — 025a887
- [x] 5.3 TUI sittings api and sitting store tests pass — 025a887
- [x] 5.4 TUI typecheck passes — 025a887

#### Manual

- [x] 5.5 POST to the back route returns the back and stays at one reveal event when repeated — 025a887

### Phase 6: The locator resolves the fragment

#### Tests

- [x] tests generated — 2a93b73

#### Automated

- [ ] 6.1 test_card_source_locator_contract.py passes
- [ ] 6.2 Remember unit suite passes
- [ ] 6.3 basedpyright reports no new errors in the remember in-memory adapters

### Phase 7: The source route and the AC-18 gate

#### Tests

- [ ] tests generated

#### Automated

- [ ] 7.1 test_card_source_query.py passes
- [ ] 7.2 test_remember_routes.py passes
- [ ] 7.3 Full backend suite passes

#### Manual

- [ ] 7.4 Source route returns 404 before the back is revealed and 200 after

### Phase 8: TUI client, view state and viewport component

#### Automated

- [ ] 8.1 TUI typecheck passes
- [ ] 8.2 TUI lint passes
- [ ] 8.3 TUI test suite passes unchanged
- [ ] 8.4 TUI build completes, confirming the new modules resolve

### Phase 9: The source view and the Esc ladder

#### Tests

- [ ] tests generated

#### Automated

- [ ] 9.1 sittingOverlay.test.tsx passes
- [ ] 9.2 TUI test suite passes
- [ ] 9.3 TUI typecheck passes

#### Manual

- [ ] 9.4 Press t then s in a live review: fragment highlighted in context, Esc returns to the card, second Esc leaves the sitting

### Phase 10: Expansion and the viewport

#### Tests

- [ ] tests generated

#### Automated

- [ ] 10.1 sourceViewport.test.tsx and sittingOverlay.test.tsx pass
- [ ] 10.2 TUI test suite passes
- [ ] 10.3 TUI lint passes

#### Manual

- [ ] 10.4 With a note longer than the terminal, scroll to the last line and confirm the marker clears and Esc lands on the card

### Phase 11: Acceptance scenarios for US-10 and US-11

#### Tests

- [ ] tests generated

#### Automated

- [ ] 11.1 Feature suite passes
- [ ] 11.2 Remember step coverage check passes
- [ ] 11.3 Full backend suite passes
