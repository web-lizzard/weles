---
change_id: auth-flow-remember-separation
current_phase: 1
next_step: 1.4
next_command: /implement auth-flow-remember-separation phase 1
updated: 2026-09-14
---

### Phase 1: Remember ownership symbols

#### Automated

- [x] 1.1 Offline backend suite passes — bd070fd
- [x] 1.2 Postgres lane passes — bd070fd
- [x] 1.3 Type check passes — bd070fd

#### Manual

- [ ] 1.4 Remember owner revision upgrades, downgrades, and re-upgrades on an emptied dev database

### Phase 2: Remember read scoping

#### Tests

- [ ] tests generated

#### Automated

- [ ] 2.1 Remember contracts pass in memory
- [ ] 2.2 Remember contracts pass on Postgres
- [ ] 2.3 Full offline suite passes
- [ ] 2.4 Type check passes

#### Manual

- [ ] 2.5 Person B has nothing due and cannot open a sitting over person A's cards over curl

### Phase 3: Sitting ownership and chain separation

#### Tests

- [ ] tests generated

#### Automated

- [ ] 3.1 Remember handler tests pass
- [ ] 3.2 Chain separation test passes
- [ ] 3.3 Full offline suite passes
- [ ] 3.4 Postgres lane passes
- [ ] 3.5 Type check passes

#### Manual

- [ ] 3.6 Person B gets 404 on person A's sitting for current card and grade over curl

### Phase 4: Per-person remember lock

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 Unit-of-work tests pass
- [ ] 4.2 Postgres remember persistence passes
- [ ] 4.3 Full offline suite passes
- [ ] 4.4 Postgres lane passes
- [ ] 4.5 Type check passes
