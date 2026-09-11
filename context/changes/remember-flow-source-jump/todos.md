---
change_id: remember-flow-source-jump
current_phase: 3
next_step: 3.1
next_command: /unit-test remember-flow-source-jump phase 3
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

### Phase 3: Non-accounting payloads stop counting

#### Tests

- [ ] tests generated

#### Automated

- [ ] 3.1 test_sitting.py passes with existing tests unmodified
- [ ] 3.2 Remember property suite passes
- [ ] 3.3 Remember unit and integration suites pass

### Phase 4: Source port, DTO, route and wiring

#### Automated

- [ ] 4.1 basedpyright reports no new errors across src
- [ ] 4.2 ruff check passes on src
- [ ] 4.3 test_remember_routes.py passes with reveal calls switched to POST

### Phase 5: Revealing the back records the fact

#### Tests

- [ ] tests generated

#### Automated

- [ ] 5.1 test_reveal_back_command.py passes
- [ ] 5.2 Remember unit and integration suites pass
- [ ] 5.3 TUI sittings api and sitting store tests pass
- [ ] 5.4 TUI typecheck passes

#### Manual

- [ ] 5.5 POST to the back route returns the back and stays at one reveal event when repeated

### Phase 6: The locator resolves the fragment

#### Tests

- [ ] tests generated

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
