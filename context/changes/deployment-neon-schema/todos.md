---
change_id: deployment-neon-schema
current_phase: 2
next_step: 2.1
next_command: /unit-test deployment-neon-schema phase 2
updated: 2026-09-14
---

### Phase 1: Schema Upgrade Stubs

#### Automated

- [x] 1.1 Add schema_upgrade module with stub symbols — a24ecfe
- [x] 1.2 basedpyright passes — a24ecfe
- [x] 1.3 Unit suite stays green — a24ecfe

### Phase 2: Schema Upgrade Behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 2.1 Implement Neon URL normalization and refusals
- [ ] 2.2 Implement schema state reading and upgrade to head
- [ ] 2.3 Unit tests for schema_upgrade pass
- [ ] 2.4 Postgres tests for schema_upgrade pass
- [ ] 2.5 basedpyright passes
- [ ] 2.6 ruff passes

### Phase 3: Migration Script and Runbook

#### Automated

- [ ] 3.1 Add scripts/migrate_database.py
- [ ] 3.2 Add README Neon schema runbook section
- [ ] 3.3 basedpyright passes on the script
- [ ] 3.4 ruff passes on scripts
- [ ] 3.5 Non-postgres suite stays green

#### Manual

- [ ] 3.6 Empty Neon branch reaches head with vector installed
- [ ] 3.7 Rerun reports already at head without prompting
- [ ] 3.8 Pooler connection string is refused with exit code 1
- [ ] 3.9 Unset NEON_DIRECT_URL is reported with exit code 1
