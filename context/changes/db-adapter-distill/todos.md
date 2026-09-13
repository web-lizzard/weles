---
change_id: db-adapter-distill
current_phase: 1
next_step: 1.5
next_command: /implement db-adapter-distill phase 1
updated: 2026-09-13
---

### Phase 1: Distill schema and Postgres repository stubs

#### Automated

- [x] 1.1 basedpyright clean
- [x] 1.2 ruff check src tests clean
- [x] 1.3 pytest -m 'not postgres' passes
- [x] 1.4 pytest -m postgres tests/integration/postgres passes

#### Manual

- [ ] 1.5 alembic upgrade head exits 0 on the dev database and current prints the distill revision as head
- [ ] 1.6 postgres MCP lists the three distill tables
- [ ] 1.7 alembic downgrade -1 removes the distill tables while capture tables remain, and upgrade head restores them

### Phase 2: Distill repositories on Postgres

#### Tests

- [ ] tests generated

#### Automated

- [ ] 2.1 pytest tests/unit/distill/contracts passes with in_memory and postgres ids
- [ ] 2.2 pytest -m postgres passes
- [ ] 2.3 pytest passes
- [ ] 2.4 basedpyright and ruff check src tests clean

### Phase 3: Distill query adapter stubs

#### Automated

- [ ] 3.1 basedpyright clean
- [ ] 3.2 ruff check src tests clean
- [ ] 3.3 pytest -m 'not postgres' passes

### Phase 4: Distill queries on Postgres

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 pytest tests/unit/distill/contracts passes with in_memory and postgres ids
- [ ] 4.2 pytest passes
- [ ] 4.3 basedpyright and ruff check src tests clean

### Phase 5: Distill unit of work stub

#### Automated

- [ ] 5.1 basedpyright clean
- [ ] 5.2 ruff check src tests clean
- [ ] 5.3 pytest -m 'not postgres' passes

### Phase 6: Unit of work, atomic commands and the capture-to-cards relay on Postgres

#### Tests

- [ ] tests generated

#### Automated

- [ ] 6.1 pytest test_distill_persistence.py and test_distill_relay.py pass
- [ ] 6.2 pytest passes
- [ ] 6.3 basedpyright and ruff check src tests clean
