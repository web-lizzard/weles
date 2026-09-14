---
change_id: auth-flow-attempt-limits
current_phase: 2
next_step: 2.1
next_command: /unit-test auth-flow-attempt-limits phase 2
updated: 2026-09-14
---

### Phase 1: Attempt ledger — stubs

#### Automated

- [x] 1.1 Type check passes — 9beea26
- [x] 1.2 Existing backend suite still passes — 9beea26

### Phase 2: Attempt ledger — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 2.1 Attempt ledger contract passes in memory
- [ ] 2.2 Attempt ledger contract passes on Postgres
- [ ] 2.3 Full backend suite passes
- [ ] 2.4 Type check passes

#### Manual

- [ ] 2.5 Migrated database shows auth_attempts table and index

### Phase 3: Limits in the authenticator — stubs

#### Automated

- [ ] 3.1 Type check passes
- [ ] 3.2 Existing backend suite still passes

### Phase 4: Limits in the authenticator — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 Authenticator tests pass
- [ ] 4.2 Full backend suite passes
- [ ] 4.3 Type check passes

### Phase 5: Source resolution and HTTP refusal — stubs

#### Automated

- [ ] 5.1 Type check passes
- [ ] 5.2 Existing backend suite still passes

### Phase 6: Source resolution and HTTP refusal — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 6.1 Source and auth HTTP tests pass
- [ ] 6.2 Full backend suite passes
- [ ] 6.3 Type check passes
- [ ] 6.4 Lint passes

#### Manual

- [ ] 6.5 Sixth wrong sign-in via curl answers 429 with Retry-After
- [ ] 6.6 Registration beyond the configured limit answers 429

### Phase 7: TUI refusal — stubs

#### Automated

- [ ] 7.1 Type check passes
- [ ] 7.2 Lint passes
- [ ] 7.3 Existing TUI suite still passes

### Phase 8: TUI refusal — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 8.1 Auth API and command tests pass
- [ ] 8.2 Full TUI suite passes
- [ ] 8.3 Type check passes
- [ ] 8.4 Lint passes

#### Manual

- [ ] 8.5 Sixth wrong weles sign-in prints the wait in minutes
