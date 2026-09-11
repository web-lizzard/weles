---
change_id: remember-flow-source-jump
current_phase: 11
next_step: epilogue
next_command: /archive remember-flow-source-jump
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

- [x] 6.1 test_card_source_locator_contract.py passes — cf7773d
- [x] 6.2 Remember unit suite passes — cf7773d
- [x] 6.3 basedpyright reports no new errors in the remember in-memory adapters — cf7773d

### Phase 7: The source route and the AC-18 gate

#### Tests

- [x] tests generated — 6aca593

#### Automated

- [x] 7.1 test_card_source_query.py passes — 88314d5
- [x] 7.2 test_remember_routes.py passes — 88314d5
- [x] 7.3 Full backend suite passes — 88314d5

#### Manual

- [x] 7.4 Source route returns 404 before the back is revealed and 200 after — 88314d5

### Phase 8: TUI client, view state and viewport component

#### Automated

- [x] 8.1 TUI typecheck passes — e5b05dc
- [x] 8.2 TUI lint passes — e5b05dc
- [x] 8.3 TUI test suite passes unchanged — e5b05dc
- [x] 8.4 TUI build completes, confirming the new modules resolve — e5b05dc

### Phase 9: The source view and the Esc ladder

#### Tests

- [x] tests generated — eb12863

#### Automated

- [x] 9.1 sittingOverlay.test.tsx passes — c06218d
- [x] 9.2 TUI test suite passes — c06218d
- [x] 9.3 TUI typecheck passes — c06218d

#### Manual

- [x] 9.4 Press t then s in a live review: fragment highlighted in context, Esc returns to the card, second Esc leaves the sitting — 4c9e59d

#### Triage

- [x] 9.5 R3-F2 Card source probe state lives in the sitting store, not overlay-local state — cddb1a7
- [x] 9.6 R3-F3 cardSourceProbe.ts is outside every phase's Changes Required — cddb1a7

### Phase 10: Expansion and the viewport

#### Tests

- [x] tests generated — b4799a7

#### Automated

- [x] 10.1 sourceViewport.test.tsx and sittingOverlay.test.tsx pass — 9bf59a6
- [x] 10.2 TUI test suite passes — 9bf59a6
- [x] 10.3 TUI lint passes — 9bf59a6

#### Manual

- [x] 10.4 With a note longer than the terminal, scroll to the last line and confirm the marker clears and Esc lands on the card — b9e9d75

### Phase 11: Acceptance scenarios for US-10 and US-11

#### Tests

- [x] tests generated — 09cefa7

#### Automated

- [x] 11.1 Feature suite passes — e37f3fa
- [x] 11.2 Remember step coverage check passes — e37f3fa
- [x] 11.3 Full backend suite passes — e37f3fa

#### Triage

- [x] 11.4 R3-F1 Phase 11 Automated Verification command collects no tests — 2d973ef
