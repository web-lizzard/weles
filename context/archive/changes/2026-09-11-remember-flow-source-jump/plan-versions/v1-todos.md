---
change_id: remember-flow-source-jump
current_phase: 1
next_step: 1.1
next_command: /implement remember-flow-source-jump phase 1
updated: 2026-09-11
---

### Phase 1: Outcome vocabulary

#### Automated

- [ ] 1.1 Remember unit suite passes unchanged
- [ ] 1.2 basedpyright reports no new errors in domain/remember

### Phase 2: Narrow showing count and draw seed to accounting outcomes

#### Tests

- [ ] tests generated

#### Automated

- [ ] 2.1 test_sitting.py passes with existing tests unmodified
- [ ] 2.2 Remember property suite passes
- [ ] 2.3 Remember unit and integration suites pass

### Phase 3: Source port, DTO, route and wiring

#### Automated

- [ ] 3.1 basedpyright reports no new errors across src
- [ ] 3.2 ruff check passes on src
- [ ] 3.3 test_remember_routes.py passes with reveal calls switched to POST

### Phase 4: Revealing the back records the fact

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 test_reveal_back_command.py passes
- [ ] 4.2 Remember unit and integration suites pass
- [ ] 4.3 TUI sittings api and sitting store tests pass
- [ ] 4.4 TUI typecheck passes

#### Manual

- [ ] 4.5 POST to the back route returns the back and stays at one reveal event when repeated

### Phase 5: The locator resolves the fragment

#### Tests

- [ ] tests generated

#### Automated

- [ ] 5.1 test_card_source_locator_contract.py passes
- [ ] 5.2 Remember unit suite passes
- [ ] 5.3 basedpyright reports no new errors in the remember in-memory adapters

### Phase 6: The source route and the AC-18 gate

#### Tests

- [ ] tests generated

#### Automated

- [ ] 6.1 test_card_source_query.py passes
- [ ] 6.2 test_remember_routes.py passes
- [ ] 6.3 Full backend suite passes

#### Manual

- [ ] 6.4 Source route returns 404 before the back is revealed and 200 after

### Phase 7: TUI client, view state and viewport component

#### Automated

- [ ] 7.1 TUI typecheck passes
- [ ] 7.2 TUI lint passes
- [ ] 7.3 TUI test suite passes unchanged
- [ ] 7.4 TUI build completes, confirming the new modules resolve

### Phase 8: The source view and the Esc ladder

#### Tests

- [ ] tests generated

#### Automated

- [ ] 8.1 sittingOverlay.test.tsx passes
- [ ] 8.2 TUI test suite passes
- [ ] 8.3 TUI typecheck passes

#### Manual

- [ ] 8.4 Press t then s in a live review: fragment highlighted in context, Esc returns to the card, second Esc leaves the sitting

### Phase 9: Expansion and the viewport

#### Tests

- [ ] tests generated

#### Automated

- [ ] 9.1 sourceViewport.test.tsx and sittingOverlay.test.tsx pass
- [ ] 9.2 TUI test suite passes
- [ ] 9.3 TUI lint passes

#### Manual

- [ ] 9.4 With a note longer than the terminal, scroll to the last line and confirm the marker clears and Esc lands on the card

### Phase 10: Acceptance scenarios for US-10 and US-11

#### Tests

- [ ] tests generated

#### Automated

- [ ] 10.1 Feature suite passes
- [ ] 10.2 Remember step coverage check passes
- [ ] 10.3 Full backend suite passes

