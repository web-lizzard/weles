---
change_id: db-adapter-outbox
current_phase: 3
next_step: 3.1
next_command: /implement db-adapter-outbox phase 3
updated: 2026-09-13
---

### Phase 1: Outbox schema and Postgres appender/claimer stubs

#### Automated

- [x] 1.1 basedpyright clean — 6e2036a
- [x] 1.2 ruff check clean over src and tests — 6e2036a
- [x] 1.3 Non-postgres suite passes — 6e2036a
- [x] 1.4 Postgres tooling suite passes with the outbox revision at head — 6e2036a

#### Manual

- [x] 1.5 Alembic CLI upgrades the dev database to the outbox revision — 6e2036a
- [x] 1.6 MCP server lists the outbox_envelopes columns — 6e2036a
- [x] 1.7 Downgrade removes outbox_envelopes and upgrade restores it — 6e2036a

### Phase 2: Postgres append and claim

#### Tests

- [x] tests generated — 3cca3ce

#### Automated

- [x] 2.1 Outbox contract suite passes for in_memory and postgres
- [x] 2.2 Postgres suite passes
- [x] 2.3 Full backend suite passes
- [x] 2.4 basedpyright and ruff clean

### Phase 3: Postgres envelope query stubs

#### Automated

- [ ] 3.1 basedpyright clean
- [ ] 3.2 ruff check clean over src and tests
- [ ] 3.3 Non-postgres suite passes

### Phase 4: Envelope state survives a fresh engine and the worker runs on Postgres

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 Outbox persistence integration tests pass
- [ ] 4.2 Full backend suite passes
- [ ] 4.3 basedpyright and ruff clean
