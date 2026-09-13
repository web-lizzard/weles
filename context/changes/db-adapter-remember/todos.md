---
change_id: db-adapter-remember
current_phase: 3
next_step: 3.1
next_command: /implement db-adapter-remember phase 3
updated: 2026-09-13
---

### Phase 1: Remember schema and Postgres repository stubs

#### Automated

- [x] 1.1 basedpyright clean — 55d47fe
- [x] 1.2 ruff check src tests clean — 55d47fe
- [x] 1.3 pytest -m 'not postgres' passes — 55d47fe
- [x] 1.4 pytest -m postgres tests/integration/postgres passes — 55d47fe

#### Manual

- [x] 1.5 alembic upgrade head exits 0 on the dev database and current prints the remember revision as head — 06b6ab0
- [x] 1.6 postgres MCP lists the four remember tables — 06b6ab0
- [x] 1.7 alembic downgrade -1 removes the remember tables while distill tables remain, and upgrade head restores them — 06b6ab0

### Phase 2: Remember repositories on Postgres

#### Tests

- [x] tests generated — f8e3a92

#### Automated

- [x] 2.1 pytest tests/unit/remember/contracts passes with in_memory and postgres ids — ca268f8
- [x] 2.2 pytest -m postgres passes — ca268f8
- [x] 2.3 pytest passes — ca268f8
- [x] 2.4 basedpyright and ruff check src tests clean — ca268f8

### Phase 3: Distill-reading catalog and source locator stubs

#### Automated

- [ ] 3.1 basedpyright clean
- [ ] 3.2 ruff check src tests clean
- [ ] 3.3 pytest -m 'not postgres' passes

### Phase 4: Catalog, source locator and remember queries on Postgres

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 pytest tests/unit/remember/contracts passes with in_memory and postgres ids
- [ ] 4.2 pytest test_remember_queries.py passes
- [ ] 4.3 pytest passes
- [ ] 4.4 basedpyright and ruff check src tests clean

### Phase 5: Remember unit of work stub

#### Automated

- [ ] 5.1 basedpyright clean
- [ ] 5.2 ruff check src tests clean
- [ ] 5.3 pytest -m 'not postgres' passes

### Phase 6: Unit of work with advisory lock, atomic commands and the rejection relay on Postgres

#### Tests

- [ ] tests generated

#### Automated

- [ ] 6.1 pytest test_remember_persistence.py and test_remember_relay.py pass
- [ ] 6.2 pytest tests/unit/remember passes
- [ ] 6.3 pytest passes
- [ ] 6.4 basedpyright and ruff check src tests clean
