---
change_id: auth-flow-sign-in-lifetime
current_phase: 3
next_step: 3.1
next_command: /implement auth-flow-sign-in-lifetime phase 3
updated: 2026-09-14
---

### Phase 1: Credential store and authorized requests — stubs

#### Automated

- [x] 1.1 Type check passes — d614f8e
- [x] 1.2 Lint passes — d614f8e

### Phase 2: Credential store and authorized requests — behavior

#### Tests

- [x] tests generated — 0a5f8a8

#### Automated

- [x] 2.1 Credential store and request tests pass — bc7b477
- [x] 2.2 Type check passes — bc7b477
- [x] 2.3 Lint passes — bc7b477

### Phase 3: Sign-in persistence, instance binding, launch guard — stubs

#### Automated

- [ ] 3.1 Type check passes
- [ ] 3.2 Lint passes
- [ ] 3.3 Existing TUI suite still passes

### Phase 4: Sign-in persistence, instance binding, launch guard — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 Launch and command tests pass
- [ ] 4.2 Full TUI suite passes
- [ ] 4.3 Type check passes
- [ ] 4.4 Lint passes

#### Manual

- [ ] 4.5 Signed-in credential file has mode 600
- [ ] 4.6 Restarted TUI launches without signing in again
- [ ] 4.7 Launch refused after switching instance address

### Phase 5: Expiry during in-progress work — stubs

#### Automated

- [ ] 5.1 Type check passes
- [ ] 5.2 Lint passes

### Phase 6: Expiry during in-progress work — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 6.1 Expiry store tests pass
- [ ] 6.2 Full TUI suite passes
- [ ] 6.3 Type check passes
- [ ] 6.4 Lint passes

#### Manual

- [ ] 6.5 Capture keeps transcript on expiry and replies after sign-in
- [ ] 6.6 Sitting shows expiry and retry records grade after sign-in
