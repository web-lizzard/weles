---
change_id: deployment-pr-gate
current_phase: 1
next_step: 1.1
next_command: /implement deployment-pr-gate phase 1
updated: 2026-09-14
---

### Phase 1: Hermetic Backend Test Bootstrap

#### Automated

- [ ] 1.1 Unit suite without postgres passes in a fresh worktree with no env
- [ ] 1.2 BDD suite passes in a fresh worktree with no env
- [ ] 1.3 Postgres unit cases pass with DATABASE_URL unset
- [ ] 1.4 Ruff and basedpyright clean

### Phase 2: Blocking Checks Workflow

#### Automated

- [ ] 2.1 Actionlint reports no errors on pr-gate.yml

#### Manual

- [ ] 2.2 Change PR runs and passes the five blocking checks

### Phase 3: Property Hunt Job

#### Automated

- [ ] 3.1 Actionlint reports no errors on pr-gate.yml
- [ ] 3.2 Property suite passes locally

#### Manual

- [ ] 3.3 Draft PR with a false property shows backend-property red and blocking checks green

### Phase 4: Protect Main

#### Automated

- [ ] 4.1 Ruleset JSON parses
- [ ] 4.2 Ruleset contexts equal workflow job names minus backend-property

#### Manual

- [ ] 4.3 Ruleset imported and active with five GitHub Actions checks
- [ ] 4.4 Direct push to main is rejected
- [ ] 4.5 PR with only backend-property red is mergeable
- [ ] 4.6 Change PR merges through the gate and main commit shows a push run
