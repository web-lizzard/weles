---
change_id: db-adapter-outbox
current_phase: 4
next_step: done
next_command: /archive db-adapter-outbox
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

- [x] 2.1 Outbox contract suite passes for in_memory and postgres — 355428f
- [x] 2.2 Postgres suite passes — 355428f
- [x] 2.3 Full backend suite passes — 355428f
- [x] 2.4 basedpyright and ruff clean — 355428f

### Phase 3: Postgres envelope query stubs

#### Automated

- [x] 3.1 basedpyright clean — fbf6d88
- [x] 3.2 ruff check clean over src and tests — fbf6d88
- [x] 3.3 Non-postgres suite passes — fbf6d88

### Phase 4: Envelope state survives a fresh engine and the worker runs on Postgres

#### Tests

- [x] tests generated — 87627d1

#### Automated

- [x] 4.1 Outbox persistence integration tests pass — 9dda8f8
- [x] 4.2 Full backend suite passes — 9dda8f8
- [x] 4.3 basedpyright and ruff clean — 9dda8f8
