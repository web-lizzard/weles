---
change_id: auth-flow-capture-distill-separation
current_phase: 4
next_step: done
next_command: /archive auth-flow-capture-distill-separation
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

- [x] tests generated — 87e09f8

#### Automated

- [x] 2.1 Capture contracts pass in memory — edbb1e6
- [x] 2.2 Capture contracts pass on Postgres — edbb1e6
- [x] 2.3 Capture unit and HTTP tests pass — edbb1e6
- [x] 2.4 Full offline suite passes — edbb1e6
- [x] 2.5 Type check passes — edbb1e6

#### Manual

- [x] 2.6 Person B gets 404 approving person A's capture session over curl — edbb1e6

### Phase 3: Distill ownership symbols

#### Automated

- [x] 3.1 Offline backend suite passes — 8272240
- [x] 3.2 Postgres lane passes — 8272240
- [x] 3.3 Type check passes — 8272240

#### Manual

- [x] 3.4 Distill owner revision upgrades, downgrades, and re-upgrades on an emptied dev database — 8272240

### Phase 4: Distill separation

#### Tests

- [x] tests generated — b1389b6

#### Automated

- [x] 4.1 Distill query contracts pass in memory — 68d7cc5
- [x] 4.2 Distill query contracts pass on Postgres — 68d7cc5
- [x] 4.3 Chain separation test passes — 68d7cc5
- [x] 4.4 Full offline suite passes — 68d7cc5
- [x] 4.5 Postgres lane passes — 68d7cc5
- [x] 4.6 Type check passes — 68d7cc5

#### Manual

- [x] 4.7 Person B sees no notes or cards of person A after background generation over curl — 68d7cc5
