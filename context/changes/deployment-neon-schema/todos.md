---
change_id: deployment-neon-schema
current_phase: 3
next_step: 3.6
next_command: /implement deployment-neon-schema phase 3
updated: 2026-09-14
---

### Phase 1: Schema Upgrade Stubs

#### Automated

- [x] 1.1 Add schema_upgrade module with stub symbols — a24ecfe
- [x] 1.2 basedpyright passes — a24ecfe
- [x] 1.3 Unit suite stays green — a24ecfe

### Phase 2: Schema Upgrade Behavior

#### Tests

- [x] tests generated — 7b5a032

#### Automated

- [x] 2.1 Implement Neon URL normalization and refusals — 01c37f9
- [x] 2.2 Implement schema state reading and upgrade to head — 01c37f9
- [x] 2.3 Unit tests for schema_upgrade pass — 01c37f9
- [x] 2.4 Postgres tests for schema_upgrade pass — 01c37f9
- [x] 2.5 basedpyright passes — 01c37f9
- [x] 2.6 ruff passes — 01c37f9

### Phase 3: Migration Script and Runbook

#### Automated

- [x] 3.1 Add scripts/migrate_database.py — d511211
- [x] 3.2 Add README Neon schema runbook section — d511211
- [x] 3.3 basedpyright passes on the script — d511211
- [x] 3.4 ruff passes on scripts — d511211
- [x] 3.5 Non-postgres suite stays green — d511211

#### Manual

- [ ] 3.6 Empty Neon branch reaches head with vector installed
- [ ] 3.7 Rerun reports already at head without prompting
- [ ] 3.8 Pooler connection string is refused with exit code 1
- [ ] 3.9 Unset NEON_DIRECT_URL is reported with exit code 1
