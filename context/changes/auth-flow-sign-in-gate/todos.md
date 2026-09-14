---
change_id: auth-flow-sign-in-gate
current_phase: 2
next_step: 2.tests
next_command: /unit-test auth-flow-sign-in-gate phase 2
updated: 2026-09-14
---

### Phase 1: Auth value objects and password hashing

#### Tests

- [x] tests generated — a825a46

#### Automated

- [x] 1.1 Auth model and hasher unit tests pass — 9a8ac80
- [x] 1.2 Type check passes — 9a8ac80

### Phase 2: Sign-in tokens and the token port contract

#### Tests

- [ ] tests generated

#### Automated

- [ ] 2.1 Token contract passes
- [ ] 2.2 Type check passes

### Phase 3: Account stores and the auth_accounts migration

#### Tests

- [ ] tests generated

#### Automated

- [ ] 3.1 In-memory contract passes
- [ ] 3.2 Postgres contract passes
- [ ] 3.3 Type check passes

#### Manual

- [ ] 3.4 Alembic upgrade, downgrade, upgrade round-trip on dev database

### Phase 4: Authenticator

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 Authenticator unit tests pass
- [ ] 4.2 Type check passes

### Phase 5: HTTP endpoints, sign-in gate, and wiring

#### Tests

- [ ] tests generated

#### Automated

- [ ] 5.1 Full backend suite passes
- [ ] 5.2 Postgres lane passes
- [ ] 5.3 Type check passes

#### Manual

- [ ] 5.4 Curl gated route refused without token
- [ ] 5.5 Curl register returns 201
- [ ] 5.6 Curl sign-in returns a token
- [ ] 5.7 Curl gated route accepted with token
- [ ] 5.8 Backend refuses to start without signing secret

### Phase 6: TUI auth API module

#### Tests

- [ ] tests generated

#### Automated

- [ ] 6.1 Regenerate schema against running backend
- [ ] 6.2 TUI auth API tests pass
- [ ] 6.3 Type check passes
- [ ] 6.4 Lint passes

### Phase 7: TUI register and sign-in commands

#### Tests

- [ ] tests generated

#### Automated

- [ ] 7.1 TUI auth command tests pass
- [ ] 7.2 Full TUI suite passes
- [ ] 7.3 Type check passes
- [ ] 7.4 Lint passes

#### Manual

- [ ] 7.5 Register from built TUI without password echo
- [ ] 7.6 Sign in from built TUI with right and wrong password
- [ ] 7.7 Piped password is refused without a request
