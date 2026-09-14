---
change_id: auth-flow-capture-distill-separation
current_phase: 3
next_step: manual
next_command: /implement auth-flow-capture-distill-separation phase 3
updated: 2026-09-14
---

### Phase 1: Capture ownership symbols

#### Automated

- [x] 1.1 Offline backend suite passes — 09fa310
- [x] 1.2 Postgres lane passes — 09fa310
- [x] 1.3 Type check passes — 09fa310

#### Manual

- [x] 1.4 Capture owner revision upgrades, downgrades, and re-upgrades on an emptied dev database — 09fa310

### Phase 2: Capture separation

#### Tests

- [ ] tests generated

#### Automated

- [ ] 2.1 Capture contracts pass in memory
- [ ] 2.2 Capture contracts pass on Postgres
- [ ] 2.3 Capture unit and HTTP tests pass
- [ ] 2.4 Full offline suite passes
- [ ] 2.5 Type check passes

#### Manual

- [ ] 2.6 Person B gets 404 approving person A's capture session over curl

### Phase 3: Distill ownership symbols

#### Automated

- [x] 3.1 Offline backend suite passes
- [x] 3.2 Postgres lane passes
- [x] 3.3 Type check passes

#### Manual

- [x] 3.4 Distill owner revision upgrades, downgrades, and re-upgrades on an emptied dev database

### Phase 4: Distill separation

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 Distill query contracts pass in memory
- [ ] 4.2 Distill query contracts pass on Postgres
- [ ] 4.3 Chain separation test passes
- [ ] 4.4 Full offline suite passes
- [ ] 4.5 Postgres lane passes
- [ ] 4.6 Type check passes

#### Manual

- [ ] 4.7 Person B sees no notes or cards of person A after background generation over curl
