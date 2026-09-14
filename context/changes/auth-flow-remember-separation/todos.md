---
change_id: auth-flow-remember-separation
current_phase: 4
next_step: 4.0
next_command: /unit-test auth-flow-remember-separation phase 4
updated: 2026-09-14
---

### Phase 1: Remember ownership symbols

#### Automated

- [x] 1.1 Offline backend suite passes — bd070fd
- [x] 1.2 Postgres lane passes — bd070fd
- [x] 1.3 Type check passes — bd070fd

#### Manual

- [x] 1.4 Remember owner revision upgrades, downgrades, and re-upgrades on an emptied dev database

### Phase 2: Remember read scoping

#### Tests

- [x] tests generated — 830db34

#### Automated

- [x] 2.1 Remember contracts pass in memory — 3275ba4
- [x] 2.2 Remember contracts pass on Postgres — 3275ba4
- [x] 2.3 Full offline suite passes — 3275ba4
- [x] 2.4 Type check passes — 3275ba4

#### Manual

- [x] 2.5 Person B has nothing due and cannot open a sitting over person A's cards over curl — 3275ba4

### Phase 3: Sitting ownership and chain separation

#### Tests

- [x] tests generated

#### Automated

- [x] 3.1 Remember handler tests pass
- [x] 3.2 Chain separation test passes
- [x] 3.3 Full offline suite passes
- [x] 3.4 Postgres lane passes
- [x] 3.5 Type check passes

#### Manual

- [x] 3.6 Person B gets 404 on person A's sitting for current card and grade over curl

### Phase 4: Per-person remember lock

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 Unit-of-work tests pass
- [ ] 4.2 Postgres remember persistence passes
- [ ] 4.3 Full offline suite passes
- [ ] 4.4 Postgres lane passes
- [ ] 4.5 Type check passes
