---
change_id: db-adapter-capture
current_phase: 6
next_step:
next_command: /archive db-adapter-capture
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

- [x] 2.1 pytest tests/unit/capture passes — abcaa25
- [x] 2.2 pytest passes — abcaa25
- [x] 2.3 basedpyright and ruff check src tests clean — abcaa25

### Phase 3: Capture schema and Postgres repository stubs

#### Automated

- [x] 3.1 basedpyright clean — 1b07ae5
- [x] 3.2 ruff check src tests clean — 1b07ae5
- [x] 3.3 pytest -m 'not postgres' passes — 1b07ae5
- [x] 3.4 pytest -m postgres tests/integration/postgres passes — 1b07ae5

#### Manual

- [x] 3.5 alembic upgrade head exits 0 on the dev database and current prints the capture revision as head — 1b07ae5
- [x] 3.6 postgres MCP finds the vector extension and the six capture tables — 1b07ae5
- [x] 3.7 alembic downgrade -1 removes the capture tables and vector extension, and upgrade head restores them — 1b07ae5

### Phase 4: Capture repositories on Postgres

#### Tests

- [x] tests generated — ef6ae33

#### Automated

- [x] 4.1 pytest tests/unit/capture/contracts passes with in_memory and postgres ids — c5918c7
- [x] 4.2 pytest -m postgres passes — c5918c7
- [x] 4.3 pytest passes — c5918c7
- [x] 4.4 basedpyright and ruff check src tests clean — c5918c7

### Phase 5: Capture unit of work and conflict stubs

#### Automated

- [x] 5.1 basedpyright clean — b0bed3d
- [x] 5.2 ruff check src tests clean — b0bed3d
- [x] 5.3 pytest -m 'not postgres' passes — b0bed3d

### Phase 6: Unit of work, optimistic concurrency and atomic commands on Postgres

#### Tests

- [x] tests generated — a557bfe

#### Automated

- [x] 6.1 pytest tests/integration/postgres/test_capture_persistence.py passes
- [x] 6.2 pytest passes
- [x] 6.3 basedpyright and ruff check src tests clean
