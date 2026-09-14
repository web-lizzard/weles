---
change_id: auth-flow-sign-in-lifetime
current_phase: 4
next_step: 4.5
next_command: /implement auth-flow-sign-in-lifetime phase 4
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

- [x] 3.1 Type check passes — 3d6a95e
- [x] 3.2 Lint passes — 3d6a95e
- [x] 3.3 Existing TUI suite still passes — 3d6a95e

### Phase 4: Sign-in persistence, instance binding, launch guard — behavior

#### Tests

- [x] tests generated — a62f906

#### Automated

- [x] 4.1 Launch and command tests pass — 4e8c8c7
- [x] 4.2 Full TUI suite passes — 4e8c8c7
- [x] 4.3 Type check passes — 4e8c8c7
- [x] 4.4 Lint passes — 4e8c8c7

#### Manual

- [ ] 4.5 Signed-in credential file has mode 600
- [ ] 4.6 Restarted TUI launches without signing in again
- [ ] 4.7 Launch refused after switching instance address

### Phase 5: Expiry during in-progress work — stubs

#### Automated

- [x] 5.1 Type check passes
- [x] 5.2 Lint passes

### Phase 6: Expiry during in-progress work — behavior

#### Tests

- [x] tests generated — e62b787

#### Automated

- [x] 6.1 Expiry store tests pass — da8be4d
- [x] 6.2 Full TUI suite passes — da8be4d
- [x] 6.3 Type check passes — da8be4d
- [x] 6.4 Lint passes — da8be4d

#### Manual

- [x] 6.5 Capture keeps transcript on expiry and replies after sign-in
- [x] 6.6 Sitting shows expiry and retry records grade after sign-in
