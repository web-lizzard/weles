---
change_id: db-adapter-capture
current_phase: 3
next_step: 3.1
next_command: /implement db-adapter-capture phase 3
updated: 2026-09-13
---

### Phase 1: Similarity port and embedding model stubs

#### Automated

- [x] 1.1 basedpyright clean — 130a5da
- [x] 1.2 ruff check src tests clean — 130a5da
- [x] 1.3 pytest -m 'not postgres' passes — 130a5da

### Phase 2: Similarity through the port, in memory

#### Tests

- [x] tests generated — 523c7a5

#### Automated

- [x] 2.1 pytest tests/unit/capture passes
- [x] 2.2 pytest passes
- [x] 2.3 basedpyright and ruff check src tests clean

### Phase 3: Capture schema and Postgres repository stubs

#### Automated

- [ ] 3.1 basedpyright clean
- [ ] 3.2 ruff check src tests clean
- [ ] 3.3 pytest -m 'not postgres' passes
- [ ] 3.4 pytest -m postgres tests/integration/postgres passes

#### Manual

- [ ] 3.5 alembic upgrade head exits 0 on the dev database and current prints the capture revision as head
- [ ] 3.6 postgres MCP finds the vector extension and the six capture tables
- [ ] 3.7 alembic downgrade -1 removes the capture tables and vector extension, and upgrade head restores them

### Phase 4: Capture repositories on Postgres

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 pytest tests/unit/capture/contracts passes with in_memory and postgres ids
- [ ] 4.2 pytest -m postgres passes
- [ ] 4.3 pytest passes
- [ ] 4.4 basedpyright and ruff check src tests clean

### Phase 5: Capture unit of work and conflict stubs

#### Automated

- [ ] 5.1 basedpyright clean
- [ ] 5.2 ruff check src tests clean
- [ ] 5.3 pytest -m 'not postgres' passes

### Phase 6: Unit of work, optimistic concurrency and atomic commands on Postgres

#### Tests

- [ ] tests generated

#### Automated

- [ ] 6.1 pytest tests/integration/postgres/test_capture_persistence.py passes
- [ ] 6.2 pytest passes
- [ ] 6.3 basedpyright and ruff check src tests clean
