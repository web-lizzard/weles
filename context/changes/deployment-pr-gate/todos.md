---
change_id: deployment-pr-gate
current_phase: 4
next_step: 4.1
next_command: /implement deployment-pr-gate phase 4
updated: 2026-09-14
---

### Phase 1: Hermetic Backend Test Bootstrap

#### Automated

- [x] 1.1 Unit suite without postgres passes in a fresh worktree with no env — e706cef
- [x] 1.2 BDD suite passes in a fresh worktree with no env — e706cef
- [x] 1.3 Postgres unit cases pass with DATABASE_URL unset — e706cef
- [x] 1.4 Ruff and basedpyright clean — e706cef

### Phase 2: Blocking Checks Workflow

#### Automated

- [x] 2.1 Actionlint reports no errors on pr-gate.yml — 7e388ff

#### Manual

- [x] 2.2 Change PR runs and passes the five blocking checks — d9bcd5d

### Phase 3: Property Hunt Job

#### Automated

- [x] 3.1 Actionlint reports no errors on pr-gate.yml — 045d88e
- [x] 3.2 Property suite passes locally — 045d88e

#### Manual

- [x] 3.3 Draft PR with a false property shows backend-property red and blocking checks green

### Phase 4: Protect Main

#### Automated

- [ ] 4.1 Ruleset JSON parses
- [ ] 4.2 Ruleset contexts equal workflow job names minus backend-property

#### Manual

- [ ] 4.3 Ruleset imported and active with five GitHub Actions checks
- [ ] 4.4 Direct push to main is rejected
- [ ] 4.5 PR with only backend-property red is mergeable
- [ ] 4.6 Change PR merges through the gate and main commit shows a push run
