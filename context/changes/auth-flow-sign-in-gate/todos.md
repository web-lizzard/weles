---
change_id: auth-flow-sign-in-gate
current_phase: 7
next_step: tests
next_command: /unit-test auth-flow-sign-in-gate phase 7
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

- [x] tests generated — b24cacc

#### Automated

- [x] 2.1 Token contract passes — 1e3a801
- [x] 2.2 Type check passes — 1e3a801

### Phase 3: Account stores and the auth_accounts migration

#### Tests

- [x] tests generated — f21bde6

#### Automated

- [x] 3.1 In-memory contract passes — 1af68a8
- [x] 3.2 Postgres contract passes — 1af68a8
- [x] 3.3 Type check passes — 1af68a8

#### Manual

- [x] 3.4 Alembic upgrade, downgrade, upgrade round-trip on dev database — 1af68a8

### Phase 4: Authenticator

#### Tests

- [x] tests generated — e0f9060

#### Automated

- [x] 4.1 Authenticator unit tests pass — ba45627
- [x] 4.2 Type check passes — ba45627

### Phase 5: HTTP endpoints, sign-in gate, and wiring

#### Tests

- [x] tests generated — c467b1a

#### Automated

- [x] 5.1 Full backend suite passes — b9800e8
- [x] 5.2 Postgres lane passes — b9800e8
- [x] 5.3 Type check passes — b9800e8

#### Manual

- [x] 5.4 Curl gated route refused without token — b9800e8
- [x] 5.5 Curl register returns 201 — b9800e8
- [x] 5.6 Curl sign-in returns a token — b9800e8
- [x] 5.7 Curl gated route accepted with token — b9800e8
- [x] 5.8 Backend refuses to start without signing secret — b9800e8

### Phase 6: TUI auth API module

#### Tests

- [x] tests generated — 88b4ef2

#### Automated

- [x] 6.1 Regenerate schema against running backend — 6244d3a
- [x] 6.2 TUI auth API tests pass — 6244d3a
- [x] 6.3 Type check passes — 6244d3a
- [x] 6.4 Lint passes — 6244d3a

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
